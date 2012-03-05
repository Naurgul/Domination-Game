class Agent(object):
    
    NAME = "mimic"
    
    UNVISITED = None
    SPAWN_LOC = []
    AMMOPACKS_LOC = {}
    AMMOPACKS_UPDATED = []
    LAST_ROUND = -1
    
    #pickle_file = open('qvalues.pickle', 'rb')
    #QVALUES = pickle.load(pickle_file)
    #pickle_file.close()
    QVALUES = None
    
    LEARNING_RATE = 0.7
    DISCOUNT_FACTOR = 0.6
    EXPLORE_PERCENTAGE = 20
    
    # TODO: Remove magic numbers

    # ===== Main functions ===============================================================================
        
    def __init__(self, id, team, settings = None, field_rects = None, field_grid = None, nav_mesh = None):
        self.id = id
        self.team = team
        self.r_old = 0
        self.s_old = None
        self.s_old = None
        self.mesh = nav_mesh
        self.grid = field_grid
        self.settings = settings
        self.goal = None
        
        self.__class__.UNVISITED = self.mesh.keys()
        
        if id == 0:
            self.all_agents = self.__class__.all_agents = []
        self.all_agents.append(self)
    
    def observe(self, observation):
        self.observation = observation
        self.selected = observation.selected
        
    def action(self):
        obs = self.observation

        # get the latest qvalue dictionary
        pickle_file = open('qvalues.pickle', 'rb')
        self.__class__.QVALUES = pickle.load(pickle_file)
        pickle_file.close()
        
        #this code only runs once, in the beginning of each match!
        if len(self.__class__.SPAWN_LOC) < 6:
            self.__class__.SPAWN_LOC.append(obs.loc)
        
        # find the CPs we have not captured yet
        not_poss_cps = filter(lambda x: x[2] != self.team, self.observation.cps)
        
        # find ammopacks within visual range
        ammopacks = filter(lambda x: x[2] == "Ammo", obs.objects)
        # compare visible ammopacks with the ones in memory
        self.updateAmmopacks(obs, ammopacks)
                 
        # if we reach an unexplored node from the mesh graph, 
        # remove it from the list of unvisited nodes           
        for x in self.__class__.UNVISITED:
            if point_dist(obs.loc, x) < self.settings.tilesize:
                self.__class__.UNVISITED.remove(x)
        
        ##################### REINFORCEMENT LEARNING #####################
        locations_and_state = self.getState(obs, not_poss_cps)
        self.s_new = locations_and_state[3]
        r = self.getReward()
        if (self.s_old and self.a_old):
                self.updateQ(self.s_old, self.a_old, self.s_new, r)

        action = self.decideAction(self.s_new)
        if (action==3):
            if self.__class__.UNVISITED:
                unv_close = self.get_closest(self.__class__.UNVISITED)
                path_unv = find_path(obs.loc, unv_close, self.mesh, self.grid, self.settings.tilesize)
                self.goal = path_unv[0]
            else:
                self.goal = None
        else:
            self.goal = locations_and_state[action][0]
        
        self.s_old = self.s_new
        self.a_old = action
        ##################### REINFORCEMENT LEARNING #####################
        
        #print extra information when selected
        self.printInfo(obs, ammopacks)

        # save the latest qvalue dictionary
        output = open('qvalues.pickle', 'wb')
        pickle.dump(self.__class__.QVALUES, output)
        output.close()  

        # return specific (low-level) actions based on goal
        return self.GoalToAction(obs)
               
    def GoalToAction(self, obs):
        # TODO: Fix agents running with top speed when they should be rotating in place.
        # if I see an enemy within range and I have ammo 
        # there's no wall (TODO: or friendly) between us,
        # shoot the motherfucker!  
        shoot = False
        if obs.ammo > 0:
            closeToEnemysSpawn = False
            
            # I have ammo. I don't shoot at enemy which is respawning
            for spawn_loc in self.__class__.SPAWN_LOC:
                if point_dist(spawn_loc, obs.loc) < 35:
                    closeToEnemysSpawn = True      
            # If I am not in the enemy's spawn area and I see some enemies in my proximity and I can shoot them without harming my friends, I do it !
            if obs.foes and not closeToEnemysSpawn:
                for enemy in obs.foes:
                    # I can shoot this enemy - he is in my shooting range and there is no wall blocking me
                    if point_dist(enemy[0:2], obs.loc) < self.settings.max_range and not    line_intersects_grid(obs.loc, enemy[0:2], self.grid, self.settings.tilesize):
                    # But I do not shoot if a friend is between me and the enemy
                        shoot = True
                        for friend in obs.friends:
                            if line_intersects_circ(obs.loc, enemy[0:2], friend[0:2], 10):
                                shoot = False
                        if shoot == True:
                            self.goal = enemy[0:2]
        
        # decide which low level actions I need to take right now
        if(self.goal):
            dx = self.goal[0] - obs.loc[0]
            dy = self.goal[1] - obs.loc[1]
            turn = angle_fix(math.atan2(dy, dx) - obs.angle)            
            if turn > self.settings.max_turn or turn < -self.settings.max_turn:
                shoot = False                
            speed = (dx**2 + dy**2)**0.5
        else:
            turn = 0
            speed = 0
        
        return (turn, speed, shoot)
    
    def printInfo(self, obs, ammopacks):
        if obs.selected:
            print "Goal: {0}".format(self.goal)
            print "State: {0}".format(self.s_old)
            print "Action: {0}".format(self.a_old)
            #print "Visible ammo: {0}".format(ammopacks)
            #print "Ammo locations: {0}".format(self.__class__.AMMOPACKS_LOC)
            #print "Ammo locations number: {0}".format(len(self.__class__.AMMOPACKS_LOC))
            pass
        
    def debug(self, surface):
        import pygame
        # First agent clears the screen
        if self.id == 0:
            surface.fill((0,0,0,0))
        # Selected agents draw their info
        if self.selected:
            if self.goal is not None:
                pygame.draw.line(surface,(0,0,0),self.observation.loc, self.goal)
        
    def finalize(self, interrupted=False):
        if (self.id == 0):
                output = open('qvalues.pickle', 'wb')
                pickle.dump(self.__class__.QVALUES, output)
                output.close()
    
    # ===== Q-learning functions ===============================================================================
    
    def getState(self, obs, not_poss_cps):
        if not_poss_cps:
            cp_close = reduce(self.min_dist, not_poss_cps)
            path_cp = find_path(obs.loc, cp_close[0:2],self.mesh, self.grid, self.settings.tilesize)
            d_cp = self.path_length(obs.loc, path_cp)
            d_cp = min(int(round(math.log(d_cp/self.settings.tilesize+1,2))),5)
        else:
            cp_close = reduce(self.min_dist, obs.cps)
            path_cp = find_path(obs.loc, cp_close[0:2],self.mesh, self.grid, self.settings.tilesize)
            d_cp = self.path_length(obs.loc, path_cp)
            d_cp = min(int(round(math.log(d_cp/self.settings.tilesize+1,2))),5)        
        
        # TODO use function get best ammopack instead
        if(self.__class__.AMMOPACKS_LOC):
            ammo_close = reduce(self.min_ammo_dist, self.__class__.AMMOPACKS_LOC)        
            path_ap = find_path(obs.loc, ammo_close, self.mesh, self.grid, self.settings.tilesize)
            d_ap = self.path_length(obs.loc, path_ap)
            d_ap = min(int(round(math.log(d_ap/self.settings.tilesize+1,2))),5)
        else:
            path_ap = path_cp
            d_ap = d_cp

        sp_enemy = ((656 - self.__class__.SPAWN_LOC[0][0]), self.__class__.SPAWN_LOC[0][1])
        path_sp = find_path(obs.loc, sp_enemy, self.mesh, self.grid, self.settings.tilesize)
        d_sp = self.path_length(obs.loc, path_sp)
        d_sp = min(int(round(math.log(d_sp/self.settings.tilesize+1,2))),5)
        
        state = (d_cp, d_ap, d_sp, 3-len(not_poss_cps), obs.ammo, len(self.__class__.AMMOPACKS_LOC))
        return (path_cp,path_ap,path_sp,state)
    
    def getReward(self):
        # TODO figure out of reward #cp is better
        self.r_new = self.observation.score[self.team]
        r = self.r_new - self.r_old
        self.r_old = self.r_new
        return r
    
    def updateQ(self, s_old, a_old, s_new, r):
        q_index = (s_old,a_old)
        if (q_index in self.__class__.QVALUES):
                q_old=self.__class__.QVALUES[q_index]
        else:
            q_old=0
        q_max=[0]
        if ((s_new,0) in self.__class__.QVALUES):
            q_max.append(self.__class__.QVALUES[(s_new,0)])
        if ((s_new,1) in self.__class__.QVALUES):
            q_max.append(self.__class__.QVALUES[(s_new,1)])
        if ((s_new,2) in self.__class__.QVALUES):
            q_max.append(self.__class__.QVALUES[(s_new,2)])
        if ((s_new,3) in self.__class__.QVALUES):
            q_max.append(self.__class__.QVALUES[(s_new,3)])
        q_max=max(q_max)
        self.__class__.QVALUES[q_index]=q_old+self.__class__.LEARNING_RATE*(r+self.__class__.DISCOUNT_FACTOR*q_max - q_old)
    
    def decideAction(self, s_new):
    	# Explore/Exploit ratio
    	if (random.randint(0, 100) <= self.__class__.EXPLORE_PERCENTAGE):
        	action = random.randint(0, 3)
    	else:
       	    action = 0
            q_value = -9999999
            for a in range(0, 4):
                if ((s_new,a) in self.__class__.QVALUES and self.__class__.QVALUES[(s_new,a)] > q_value):
                    action = a
                    q_value = self.__class__.QVALUES[(s_new,a)]
        return action
    
    # ===== AmmoPack functions ===============================================================================

    def updateAmmopacks(self, obs, ammopacks):
        
        # if I see an ammopack for the first time
        # add both that one and its symmetric to the list of ammopack locations
        for pack in ammopacks:
            #print "AMMOPACKS_X: ", pack        
            self.__class__.AMMOPACKS_LOC[(pack[0], pack[1])] = 20
            self.__class__.AMMOPACKS_LOC[(656 - pack[0], pack[1])] = 20 # 656 is the width of the screen in pixels
            
        # ammopacks can be updated at most once per turn
        # empty the ammo location blacklist if it's a new round
        if self.newRound():
           self.__class__.AMMOPACKS_UPDATED = []   

        # for ammopacks that should be visible:
        #   t=20 if I see them
        #   t=0 if I don't see them
        # for ammopacks outside my range:
        #   increment t by 1
        
        if self.__class__.AMMOPACKS_LOC != {}:
            for pack_loc in self.__class__.AMMOPACKS_LOC:
                if point_dist(pack_loc, obs.loc) < 100 :

                    #found = False
                    #for pack in ammopacks:
                        #if pack[0:2] == pack_loc:
                            #found = True
                    
                    found = pack_loc in map(lambda x:x[0:2], ammopacks)
                    if found:
                        self.__class__.AMMOPACKS_LOC[pack_loc] = 20
                    elif self.__class__.AMMOPACKS_LOC[pack_loc] == 20:
                        self.__class__.AMMOPACKS_LOC[pack_loc] = 1
                    elif pack_loc in self.__class__.AMMOPACKS_UPDATED:
                        self.__class__.AMMOPACKS_LOC[pack_loc] = min( 20, self.__class__.AMMOPACKS_LOC[pack_loc] + 1 )
                        self.__class__.AMMOPACKS_UPDATED.append[pack_loc]
                else:
                    self.__class__.AMMOPACKS_LOC[pack_loc] = min( 20, self.__class__.AMMOPACKS_LOC[pack_loc] + 1 )
    
    def getBestTarget(self, ammopacks, obs):
        #TODO: check path length or ray trace to make sure we're not going around walls
        everyone = obs.friends + obs.foes
        everyone.append(obs.loc)
        #print everyone
        good_ammopacks = filter(lambda pack: self.whoIsTheClosest(everyone, pack) == obs.loc, ammopacks)
        if len(good_ammopacks) > 0:
            return reduce(self.min_dist, good_ammopacks)
        else:
            return None  
            
    # ===== Auxilliary functions =====           
    
    def compare_spawn_dist(self, cp_loc):
        path = find_path(self.observation.loc, cp_loc[0:2], self.mesh, self.grid, self.settings.tilesize)
        return self.path_length(self.__class__.SPAWN_LOC, path)
    
    def path_length(self, prev, path):
        length = 0
        for node in path:
            length += point_dist(prev, node)
            prev = node
        return length

    def get_closest(self, points):
        closest_point=points[0]
        path=find_path(self.observation.loc, closest_point, self.mesh, self.grid, self.settings.tilesize)
        closest_dist=self.path_length(self.observation.loc,path)
        for point in points:
            path=find_path(self.observation.loc, point, self.mesh, self.grid, self.settings.tilesize)
            dist=self.path_length(self.observation.loc,path)
            if (dist < closest_dist):
                closest_point=point
                closest_dist=dist
 
        return closest_point
    
    def min_dist(self, loc1, loc2):
        path1 = find_path(self.observation.loc, loc1[0:2], self.mesh, self.grid, self.settings.tilesize)
        path2 = find_path(self.observation.loc, loc2[0:2], self.mesh, self.grid, self.settings.tilesize)
        if self.path_length(self.observation.loc, path1) < self.path_length(self.observation.loc, path2):
            return loc1[0:2]
        else:
            return loc2[0:2]
        
    def min_ammo_dist(self, ammo_loc1, ammo_loc2):
        WEIGHT = 750
        path1 = find_path(self.observation.loc, ammo_loc1[0:2], self.mesh, self.grid, self.settings.tilesize)
        path2 = find_path(self.observation.loc, ammo_loc2[0:2], self.mesh, self.grid, self.settings.tilesize)
        d1 = (self.path_length(self.observation.loc, path1) + WEIGHT / self.__class__.AMMOPACKS_LOC[ammo_loc1] )
        d2 = (self.path_length(self.observation.loc, path2) + WEIGHT / self.__class__.AMMOPACKS_LOC[ammo_loc2] )
        if (d1 < d2):
            return ammo_loc1
        else:
            return ammo_loc2
        
    def whoIsTheClosest(self, loc_list, target):
        min_dist = float("inf")
        min_loc = None
        for loc in loc_list:
            dist = point_dist(loc, target)
            if dist < min_dist:
                min_dist = dist
                min_loc = loc
        
        return min_loc

    def newRound(self):
        if self.observation.step > self.__class__.LAST_ROUND:
            self.__class__.LAST_ROUND = self.observation.step
            return True
        else:
            self.__class__.LAST_ROUND = self.observation.step
            return False
