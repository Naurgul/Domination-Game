class Agent(object):
    
    NAME = "warmain"
    SCOUTS = []
    UNVISITED = None
    
    SPAWN_LOC = []
    AMMOPACKS_LOC = {}
    #CPS_LOC = []
    
    # TODO: Remove magic numbers 

    def __init__(self, id, team, settings = None, field_rects = None, field_grid = None, nav_mesh = None):
        self.id = id
        self.team = team
        self.mesh = nav_mesh
        self.grid = field_grid
        self.settings = settings
        self.goal = None
        self.scout_goal = None
        
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
        
        # TODO: do not shoot if enemies are in the spawn area        
        
        if len(self.__class__.SPAWN_LOC) < 6:
            self.__class__.SPAWN_LOC.append(obs.loc)
            
        #print "Spawn loc: ", self.__class__.SPAWN_LOC
            #self.__class__.SPAWN_LOC.append(obs.loc)
            #self.__class__.CPS_LOC = obs.cps[:]
            #self.__class__.CPS_LOC.sort(key = self.compare_spawn_dist)
            #print "CPS_LOC: ", self.__class__.CPS_LOC
        
        # find the CPs we have not captured yet
        not_poss_cps = filter(lambda x: x[2] != self.team, self.observation.cps)
        # find ammopacks within visual range
        ammopacks = filter(lambda x: x[2] == "Ammo", obs.objects)
        # compare visible ammopacks with the ones in memory
        self.updateAmmopacks(obs, ammopacks)
        
        # remove goal if reached    
        if self.goal is not None and point_dist(self.goal, obs.loc) < self.settings.tilesize:
            self.goal = None
             
        # if we reach an unexplored node from the mesh graph, 
        # remove it from the list of unvisited nodes           
        for x in self.__class__.UNVISITED:
            if point_dist(obs.loc, x) < self.settings.tilesize:
                self.__class__.UNVISITED.remove(x)
        
        # decide who is scouting 
        self.whoIsScout(obs, not_poss_cps)   
        
        # decide behaviour based on role    
        if self.id in self.__class__.SCOUTS:
            self.scoutBehaviour(ammopacks, obs)
        else:            
            self.trooperBehaviour(obs, ammopacks, not_poss_cps)       
            
        #print extra information when selected
        self.printInfo(obs, ammopacks)
        
        # return specific (low-level) actions based on goal
        return self.GoalToAction(obs)
        
    
    def updateAmmopacks(self, obs, ammopacks):
        
        # if I see an ammopack for the first time
        # add both that one and its symmetric to the list of ammopack locations
        for pack in ammopacks:
            #print "AMMOPACKS_X: ", pack        
            self.__class__.AMMOPACKS_LOC[(pack[0], pack[1])] = 20
            self.__class__.AMMOPACKS_LOC[(656 - pack[0], pack[1])] = 20 # 656 is the width of the screen in pixels

        
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
                    else:
                        self.__class__.AMMOPACKS_LOC[pack_loc] = min( 20, self.__class__.AMMOPACKS_LOC[pack_loc] + 1 )
                else:
                    self.__class__.AMMOPACKS_LOC[pack_loc] = min( 20, self.__class__.AMMOPACKS_LOC[pack_loc] + 1 )
                
    def whoIsScout(self, obs, not_poss_cps):
        
        MAX_SCOUTS = 6 / (len(not_poss_cps)+1)
        #print MAX_SCOUTS
        # if no one is scouting and I don't have ammo
        # and I am not too close to my goal (unless I have no goal)
        if len(self.__class__.SCOUTS) < MAX_SCOUTS and obs.ammo == 0 and ( self.goal is None or point_dist(obs.loc, self.goal) > 30 ):
            self.__class__.SCOUTS.append(self.id)     
            
        # If I am the scout and just found some ammo
        # then I stop being the scout
        if self.id in self.__class__.SCOUTS and obs.ammo > 0:
            self.__class__.SCOUTS.remove(self.id)
            self.goal = None
        
    def trooperBehaviour(self, obs, ammopacks, not_poss_cps):
        
        # remove goal if it is a CP we already control
        if self.goal is not None and self.goal not in map(lambda x: x[0:2], not_poss_cps):
            self.goal = None            
        
        # if I have no goal, 
        if self.goal is None:
            # go to the CP closest to our spawn area that we don't own
            # TODO: Avoid doing this every round!
            # TODO: Base sorting on current distance instead of distance from spawn area!
            
            if len(not_poss_cps) > 0:
                closest_cp = reduce(self.min_dist, not_poss_cps)
                self.goal = closest_cp[0:2]
            # if we control all the CPs and I have ammo, 
            # go spawn camping
            # TODO: Prevent shooting agents in the spawn area that are not spawned yet.
            elif obs.ammo > 0:
                self.goal = (656 - self.__class__.SPAWN_LOC[0][0], self.__class__.SPAWN_LOC[0][1])
            else: # else pick a random CP 
                self.goal = self.observation.cps[random.randint(0,2)][0:2]
                
        # if I pass close to an ammopack,
        # then I should go get it
        if ammopacks:
            ammopacks_close = filter(lambda x: point_dist(x[0:2], obs.loc) < 30, ammopacks)
            bestpack = self.getBestAmmopack(ammopacks_close, obs)
            if bestpack is not None:
                self.goal = bestpack[0:2]
        
        # TODO: take into account the number of enemies near the CP?
                
    
    def scoutBehaviour(self, ammopacks, obs):  
                
        #print "MY LOCATION: ", obs.loc
        
        # if there is an ammopack close by
        # go get it
        
        if ammopacks:
            bestpack = self.getBestAmmopack(ammopacks, obs) 
            if bestpack is not None:
                self.goal = bestpack[0:2]
            #print "Ammopack right ahead!"
                        
        # else, check my list of ammopack locations and go towards the best one
        if self.goal is None and len(self.__class__.AMMOPACKS_LOC) > 0:
            best_ammo_loc = reduce(self.min_ammo_dist, self.__class__.AMMOPACKS_LOC)
            #print "{0}\t{1}".format(closest_ammo, self.__class__.AMMOPACKS_LOC)
            # go there if you think you have a good chance of finding ammo there
            if self.__class__.AMMOPACKS_LOC[best_ammo_loc] > 10 or len(self.__class__.UNVISITED) == 0:
                self.goal = best_ammo_loc
                #print "There was an ammopack around here somewhere..."
                
        # if all else fails, start exploring unvisited nodes
        if self.goal is None:                    
            closest_node = reduce(self.min_dist, self.__class__.UNVISITED)
            self.goal = closest_node       
            #print "Let's go exploring!"
            
        # TODO: If I pass close to a CP we don't control and no one else is around, I should capture it
            
    def GoalToAction(self, obs):
        
        # TODO: Fix agents running with top speed when they should be rotating in place.
        
        # if I see an enemy within range and I have ammo 
        # there's no wall (TODO: or friendly) between us,
        # shoot the motherfucker!  
        shoot = False
        
        #if (obs.ammo > 0 and obs.foes and 
            #point_dist(obs.foes[0][0:2], obs.loc) < self.settings.max_range
            #and not line_intersects_grid(obs.loc, obs.foes[0][0:2], self.grid, self.settings.tilesize)):            
            #self.goal = obs.foes[0][0:2]
            #shoot = True
            
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
        pass    
    
    
    
    
    
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
        if point_dist(self.observation.loc, loc1[0:2]) < point_dist(self.observation.loc, loc2[0:2]):
            return loc1[0:2]
        else:
            return loc2[0:2]
        
    def min_ammo_dist(self, ammo_loc1, ammo_loc2):
        WEIGHT = 750
        d1 = (point_dist(self.observation.loc, ammo_loc1) + WEIGHT / self.__class__.AMMOPACKS_LOC[ammo_loc1] )
        d2 = (point_dist(self.observation.loc, ammo_loc2) + WEIGHT / self.__class__.AMMOPACKS_LOC[ammo_loc2] )
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
            

    
    
