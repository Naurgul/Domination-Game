class Agent(object):
    
    NAME = "mimic"
    
    UNVISITED = None
    SPAWN_LOC = []
    AMMOPACKS_LOC = {}
    
    pickle_file = open('qvalues.pickle', 'rb')
    QVALUES = pickle.load(pickle_file)
    pickle_file.close()
    
    # TODO: Remove magic numbers 
        
    def __init__(self, id, team, settings = None, field_rects = None, field_grid = None, nav_mesh = None):
        self.id = id
        self.team = team
        self.r_old = 0
        self.s_old = 111111
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
        # shorthand for observations
        obs = self.observation
          
        # TODO: fill in roles for dead tanks
        # TODO: replace all distances with path lengths (or do ray traces at least)
        
        #save spawn area
        #this code only runs once, in the beginning of each match!
        if len(self.__class__.SPAWN_LOC) < 6:
            self.__class__.SPAWN_LOC.append(obs.loc)
            #self.__class__.CPS_LOC = obs.cps[:]
            #self.__class__.CPS_LOC.sort(key = self.compare_spawn_dist)
            #print "CPS_LOC: ", self.__class__.CPS_LOC
        
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
        
        #self.s_new = self.getState(obs, not_poss_cps)
        #r = self.getReward()
        #self.updateQ(self.s_old, self.a_old, self.s_new, r)
        #goal = self.decideAction(self.s_new)
        #self.goal = s_new[action]
        
        #self.s_old = self.s_new
        #self.a_old = self.goal
        self.getReward()
        self.goal = reduce(self.min_dist, not_poss_cps)[0:2]
        
        #print extra information when selected
        self.printInfo(obs, ammopacks)
        
        # return specific (low-level) actions based on goal
        return self.GoalToAction(obs)
               
    def GoalToAction(self, obs):
        # TODO: Fix agents running with top speed when they should be rotating in place.
        # if I see an enemy within range and I have ammo 
        # there's no wall (TODO: or friendly) between us,
        # shoot the motherfucker!  
        shoot = False
        if (obs.ammo > 0 and obs.foes and 
            point_dist(obs.foes[0][0:2], obs.loc) < self.settings.max_range
            and not line_intersects_grid(obs.loc, obs.foes[0][0:2], self.grid, self.settings.tilesize)):            
            self.goal = obs.foes[0][0:2]
            shoot = True
        
        # use the mesh to find a path to my goal    
        path = find_path(obs.loc, self.goal, self.mesh, self.grid, self.settings.tilesize)
        
        # use the path to decide the low level actions I need to take right now
        if path:
            dx = path[0][0] - obs.loc[0]
            dy = path[0][1] - obs.loc[1]
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
            #print "Scouting: {0}".format(self.__class__.SCOUT == self.id) 
            #print "Goal: {0}".format(self.goal)
            #print "Visible ammo: {0}".format(ammopacks)
            #print "Ammo locations: {0}".format(self.__class__.AMMOPACKS_LOC)
            #print "Ammo locations number: {0}".format(len(self.__class__.AMMOPACKS_LOC))
            pass
        
    def debug(self, surface):
        """ Allows the agents to draw on the game UI,
            Refer to the pygame reference to see how you can
            draw on a pygame.surface. The given surface is
            not cleared automatically. Additionally, this
            function will only be called when the renderer is
            active, and it will only be called for the active team.
        """
        import pygame
        # First agent clears the screen
        if self.id == 0:
            surface.fill((0,0,0,0))
        # Selected agents draw their info
        if self.selected:
            if self.goal is not None:
                pygame.draw.line(surface,(0,0,0),self.observation.loc, self.goal)
        
    def finalize(self, interrupted=False):
        """ This function is called after the game ends, 
            either due to time/score limits, or due to an
            interrupt (CTRL+C) by the user. Use it to
            store any learned variables and write logs/reports.
        """
        if (self.id == 0):
        	output = open('qvalues.pickle', 'wb')
		pickle.dump(self.__class__.QVALUES, output)
		output.close()
    
    # ===== Q-learning functions =====
    
    def getState(self, obs, not_poss_cps):
        cp_close = reduce(self.min_dist, not_poss_cps)
        path_cp = find_path(obs.loc, cp_close,self.mesh, self.grid, self.settings.tilesize)
        d_cp = self.path_length(obs.loc, path_cp)
        d_cp = min(round(math.log(d_cp/self.settings.tilesize+1,2)),5)
        
        # TODO use function get best ammopack instead
        ammo_close = reduce(self.min_ammo_dist, self.__class__.AMMOPACKS_LOC)        
        path_ap = find_path(obs.loc, ammo_close, self.mesh, self.grid, self.settings.tilesize)
        d_ap = self.path_length(obs.loc, path_ap)
        d_ap = min(round(math.log(d_ap/self.settings.tilesize+1,2)),5)
        #d_ap = 1

        s = (656 - self.__class__.SPAWN_LOC[0], self.__class__.SPAWN_LOC[1])
    	path_s = find_path(obs.loc, s, self.mesh, self.grid, self.settings.tilesize)
        d_s = self.path_length(obs.loc, path_s)
        
        state=d_cp*1000000 + d_ap*100000 + obs.ammo*10000 + 3-len(not_poss_cps)*1000 + len(self.__class__.AMMOPACKS_LOC)*100 + d_s*10
        return (state,cp_close[0:2],ammo_close[0:2],s[0:2]) # d_cp, d_ap, obs.ammo, 3-len(not_poss_cps), len(self.__class__.AMMOPACKS_LOC), d_s
    
    def getReward(self):
        self.r_new = self.observation.score[self.team]
        r = self.r_new - self.r_old
        self.r_old = self.r_new
        return r
    
    def updateQ(self, s_old, a_old, s_new, r):
        q_index = s_old + a_old
        if (q_index in self.__class__.QVALUES):
            self.__class__.QVALUES[q_index]=10
        else:
            self.__class__.QVALUES[q_index]=10
    
    def decideAction(self, s_new):
        action = 1
        qvalue = self.__class__.QVALUES[s_new+action]
        
        if (self.__class__.QVALUES[s_new+2] > qvalue):
            action = 2
            qvalue = self.__class__.QVALUES[s_new+action]
            
        if (self.__class__.QVALUES[s_new+3] > qvalue):
            action = 3
            qvalue = self.__class__.QVALUES[s_new+action]
        
        if (self.__class__.QVALUES[s_new+4] > qvalue):
            action = 4
            qvalue = self.__class__.QVALUES[s_new+action]
            
        # TODO Qlearning Exploration

        return action
    
    # ===== AmmoPack functions =====

    def updateAmmopacks(self, obs, ammopacks):
        # if I see an ammopack for the first time
        # add both that one and its symmetric to the list of ammopack locations
        for pack in ammopacks:
            #print "AMMOPACKS_X: ", pack        
            self.__class__.AMMOPACKS_LOC[(pack[0], pack[1])] = 20
            self.__class__.AMMOPACKS_LOC[(656 - pack[0], pack[1])] = 20 # 656 is the width of the screen in pixels

        # TODO add some kind of boolean that indicates if a teammember already updated the time
        # for ammopacks that should be visible:
        #   t=20 if I see them
        #   t=0 if I don't see them
        # for ammopacks outside my range:
        #   increment t by 1
        
        if self.__class__.AMMOPACKS_LOC != {}:
            for pack_loc in self.__class__.AMMOPACKS_LOC:
                if point_dist(pack_loc, obs.loc) < 100 :
                    found = False
                    for pack in ammopacks:
                        if pack[0:2] == pack_loc:
                            found = True
                    if found:
                        self.__class__.AMMOPACKS_LOC[pack_loc] = 20
                    elif self.__class__.AMMOPACKS_LOC[pack_loc] == 20:
                        self.__class__.AMMOPACKS_LOC[pack_loc] = 1
                    else:
                        self.__class__.AMMOPACKS_LOC[pack_loc] = min( 20, self.__class__.AMMOPACKS_LOC[pack_loc] + 1 )
                else:
                    self.__class__.AMMOPACKS_LOC[pack_loc] = min( 20, self.__class__.AMMOPACKS_LOC[pack_loc] + 1 )
    
    def getBestAmmopack(self, ammopacks, obs):
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
        #print "{2} {0} - {1}".format(path, length, self.observation.loc)
        return length
    
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
            #print "{0}<{1}".format(d1, d2)
            return ammo_loc1
        else:
            #print "{0}<{1}".format(d2, d1)
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
