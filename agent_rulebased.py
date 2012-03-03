class Agent(object):
    
    NAME = "warmain"
    SCOUTS = []
    TEAMMATES = []
    ENEMIES = []
    UNVISITED = None
    
    SPAWN_LOC = []
    AMMOPACKS_LOC = {}
    AMMOPACKS_UPDATED = []
    LAST_ROUND = -1
    
    GOALS = []
    
    #CPS_LOC = []
    
    # ===== Constants =====
    
    FIRST_AGENT_ID = 0
    TEAM_SIZE = 6
    MAP_WIDTH = 656
    SHORT_DISTANCE = 30
    VERY_SHORT_DISTANCE = 10
    NUM_POINTS = 3
    NUM_AMMO_LOCS = 6
    AMMO_EXPECTATION_WEIGHT = 750
    EXPLORE_WAIT_STEPS = 50
    DISTANCE_TURN_IN_PLACE = 10 # also changed in init
    
    # ===============
    

    def __init__(self, id, team, settings = None, field_rects = None, field_grid = None, nav_mesh = None):
        self.id = id
        self.team = team
        self.mesh = nav_mesh
        self.grid = field_grid
        self.settings = settings
        self.goal = None
        self.scout_goal = None
        
        self.__class__.UNVISITED = self.mesh.keys()
        
        if id == self.__class__.FIRST_AGENT_ID:
            self.all_agents = self.__class__.all_agents = []
        self.all_agents.append(self)

        DISTANCE_TURN_IN_PLACE = self.settings.max_speed / 4
    
    def observe(self, observation):
        self.observation = observation
        self.selected = observation.selected
        
        # Reinitialize the ENEMIES list each round
        
        if self.id == 0:
            self.__class__.ENEMIES = []
            
        # Add the positions of the teammates to the TEAMMATES list
        
        if len(self.__class__.TEAMMATES) < self.__class__.TEAM_SIZE:
            self.__class__.TEAMMATES.insert(self.id, observation.loc)
        else:
            self.__class__.TEAMMATES[self.id] = observation.loc
            
        # Add the position of any observable enemy to the ENEMIES list
            
        if observation.foes:
            for enemy in observation.foes:
                if not enemy in self.__class__.ENEMIES:
                    self.__class__.ENEMIES.append(enemy)
                    
        #print "Agent ID: ", self.id
        
    def action(self):
        
        # shorthand for observations
        obs = self.observation
          
        # TODO: fill in roles for dead tanks
        # TODO: replace all distances with path lengths (or do ray traces at least)
        
        #save spawn area
        #this code only runs once, in the beginning of each match!             
        
        if len(self.__class__.SPAWN_LOC) < self.__class__.TEAM_SIZE:
            self.__class__.SPAWN_LOC.append(obs.loc)
            
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
        for node in self.__class__.UNVISITED:
            if point_dist(obs.loc, node) < self.settings.tilesize:
                self.__class__.UNVISITED.remove(node)
        
        # decide who is scouting 
        self.whoIsScout(obs, not_poss_cps)   
        
        # decide behaviour based on role    
        if self.id in self.__class__.SCOUTS:
            self.scoutBehaviour(ammopacks, obs, not_poss_cps)
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
            self.__class__.AMMOPACKS_LOC[(pack[0], pack[1])] = self.settings.ammo_rate
            self.__class__.AMMOPACKS_LOC[(self.__class__.MAP_WIDTH - pack[0], pack[1])] = self.settings.ammo_rate
            
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
                if point_dist(pack_loc, obs.loc) < self.settings.max_see :

                    #found = False
                    #for pack in ammopacks:
                        #if pack[0:2] == pack_loc:
                            #found = True
                    
                    found = pack_loc in map(lambda x:x[0:2], ammopacks)
                    if found:
                        self.__class__.AMMOPACKS_LOC[pack_loc] = self.settings.ammo_rate
                    elif self.__class__.AMMOPACKS_LOC[pack_loc] == self.settings.ammo_rate:
                        self.__class__.AMMOPACKS_LOC[pack_loc] = 1
                    elif pack_loc not in self.__class__.AMMOPACKS_UPDATED:
                        self.__class__.AMMOPACKS_LOC[pack_loc] = min( self.settings.ammo_rate, self.__class__.AMMOPACKS_LOC[pack_loc] + 1 )
                        self.__class__.AMMOPACKS_UPDATED.append(pack_loc)
                elif pack_loc not in self.__class__.AMMOPACKS_UPDATED:
                    self.__class__.AMMOPACKS_LOC[pack_loc] = min( self.settings.ammo_rate, self.__class__.AMMOPACKS_LOC[pack_loc] + 1 )
                    self.__class__.AMMOPACKS_UPDATED.append(pack_loc)
                
    def whoIsScout(self, obs, not_poss_cps):

        #TODO: 1. add LOW_AMMO constant, 2. if all CPs ours, some (or one) with lowest ammo go for ammo
        
        MAX_SCOUTS = self.__class__.TEAM_SIZE / (len(not_poss_cps)+1)
        #print MAX_SCOUTS
        # if no one is scouting and I don't have ammo
        # and I am not too close to my goal (unless I have no goal)
        if len(self.__class__.SCOUTS) < MAX_SCOUTS and obs.ammo == 0 and ( self.goal is None or point_dist(obs.loc, self.goal) > self.__class__.SHORT_DISTANCE ):
            self.__class__.SCOUTS.append(self.id)     
            
        # If I am the scout and just found some ammo
        # then I stop being the scout
        if self.id in self.__class__.SCOUTS and obs.ammo > 0:
            self.__class__.SCOUTS.remove(self.id)
            self.goal = None
        
    def trooperBehaviour(self, obs, ammopacks, not_poss_cps):
        
        # TODO: If enemy is nearest to CP we own, start going back to recapture
        # TODO: Same situation, if we have ammo, set goal to enemy        
        # TODO: Change goal if too many agents have the same goal as you do 
        
        # remove goal if it is a CP we already control
        if self.goal is not None and self.goal not in map(lambda x: x[0:2], not_poss_cps):
            self.goal = None            
        
        # if I have no goal, 
        if self.goal is None:
            # go to the CP closest to our spawn area that we don't own

            if len(not_poss_cps) > 0:
                closest_cp = reduce(self.min_dist, not_poss_cps)
                self.goal = closest_cp[0:2]
            # if we control all the CPs and I have ammo, 
            # go spawn camping
            elif obs.ammo > 0:
                self.goal = (self.__class__.MAP_WIDTH - self.__class__.SPAWN_LOC[0][0], self.__class__.SPAWN_LOC[0][1])
            else: # else pick a random CP 
                self.goal = self.observation.cps[random.randint(0,self.__class__.NUM_POINTS-1)][0:2]
                
        # if I pass close to an ammopack,
        # then I should go get it
        if ammopacks:
            ammopacks_close = filter(lambda x: point_dist(x[0:2], obs.loc) < self.__class__.SHORT_DISTANCE, ammopacks)
            bestpack = self.getBestAmmopack(ammopacks_close, obs)
            if bestpack is not None:
                self.goal = bestpack[0:2]
        
        # TODO: take into account the number of enemies near the CP?
                
    
    def scoutBehaviour(self, ammopacks, obs, not_poss_cps):  
                
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
            if self.__class__.AMMOPACKS_LOC[best_ammo_loc] > self.settings.ammo_rate / 2:
                self.goal = best_ammo_loc
                #print "There was an ammopack around here somewhere..."
                
        # if we have not found all the ammo locations, start exploring unvisited nodes
        if self.goal is None and len(self.__class__.AMMOPACKS_LOC) < self.__class__.NUM_AMMO_LOCS and self.observation.step > self.__class__.EXPLORE_WAIT_STEPS:                    
            closest_node = reduce(self.min_dist, self.__class__.UNVISITED)
            self.goal = closest_node       
            #print "Let's go exploring!"

        #if all else fails, stop being a scout
        if self.goal is None:
            self.__class__.SCOUTS.remove(self.id)
            self.trooperBehaviour(obs, ammopacks, not_poss_cps)
            
        # TODO: If I pass close to a CP we don't control and no one else is around, I should capture it
            
    def GoalToAction(self, obs):
        
        # TODO: Fix agents running with top speed when they should be rotating in place.
        # TODO: Jiggle around if you're not going anywhere
        
        # if I see an enemy within range and I have ammo 
        # there's no wall (TODO: or friendly) between us,
        # shoot the motherfucker!  BAD LANGUAGE!!
        shoot = False
        
        #if (obs.ammo > 0 and obs.foes and 
            #point_dist(obs.foes[0][0:2], obs.loc) < self.settings.max_range
            #and not line_intersects_grid(obs.loc, obs.foes[0][0:2], self.grid, self.settings.tilesize)):            
            #self.goal = obs.foes[0][0:2]
            #shoot = True
            
            
        if obs.ammo > 0:
            closeToEnemysSpawn = False
            
            # I have ammo. I don't shoot at enemy which is respawning
            
            #for spawn_loc in self.__class__.SPAWN_LOC:
                #if point_dist((656 - spawn_loc[0], spawn_loc[1]), obs.loc) < 35:
                    #closeToEnemysSpawn = True
                    
            # If I am not in the enemy's spawn area and I see some enemies in my proximity and I can shoot them without harming my friends, I do it !
            
            possible_targets_list = []

            if obs.foes:
                for enemy in obs.foes:
                    # I can shoot this enemy; he is in my shooting range and there are no walls blocking me
                    if point_dist(enemy[0:2], obs.loc) < self.settings.max_range and not line_intersects_grid(obs.loc, enemy[0:2], self.grid, self.settings.tilesize):
                        shoot = True

                        # but I do not shoot if a friend is between us
                        for friend in obs.friends:
                            if line_intersects_circ(obs.loc, enemy[0:2], friend[0:2], self.__class__.VERY_SHORT_DISTANCE):
                                shoot = False

                        # and I do not shoot at respawning enemy
                        for spawn_loc in self.__class__.SPAWN_LOC:
                            if point_dist((self.__class__.MAP_WIDTH - spawn_loc[0], spawn_loc[1]), enemy) < self.settings.tilesize:
                                shoot = False

                        # if after all I can shoot this target then add him to the list
                        if shoot == True:
                            #self.goal = enemy[0:2]
                            possible_targets_list.append(enemy[0:2])
                            #break # with this the first found in list that is able to be shot at, gets shot

            # find the one you need to turn the least to face and shoot him down
            if possible_targets_list:
                self.goal = reduce(self.min_turn, possible_targets_list)
                if self.goal is not None:
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
            #if point_dist(obs.loc, path[0]) < self.__class__.DISTANCE_TURN_IN_PLACE and math.fabs(turn) >= self.settings.max_turn:
            #    speed = 0
            
        else:
            turn = 0
            speed = 0
            
        # Add the current goal to the GOALS list
            
        if len(self.__class__.GOALS) < self.__class__.TEAM_SIZE:
            self.__class__.GOALS.append(self.goal)
        else:
            self.__class__.GOALS[self.id] = self.goal
        
        return (turn, speed, shoot)

    def printInfo(self, obs, ammopacks):
        if obs.selected:
            #print "Scouting: {0}".format(self.__class__.SCOUT == self.id) 
            #print "Goal: {0}".format(self.goal)
            #print "Visible ammo: {0}".format(ammopacks)
            #print "Ammo locations: {0}".format(self.__class__.AMMOPACKS_LOC)
            #print "Ammo locations number: {0}".format(len(self.__class__.AMMOPACKS_LOC))
            #print "Locations of teammates: ", self.__class__.TEAMMATES
            #print "Locations of enemies: ", self.__class__.ENEMIES
            print "Current goals: ", self.__class__.GOALS
            
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
    
    def min_dist_fast(self, loc1, loc2):
        if point_dist(self.observation.loc, loc1[0:2]) < point_dist(self.observation.loc, loc2[0:2]):
            return loc1[0:2]
        else:
            return loc2[0:2]
        
    def min_dist(self, loc1, loc2):
        path1 = find_path(self.observation.loc, loc1[0:2], self.mesh, self.grid, self.settings.tilesize)
        path2 = find_path(self.observation.loc, loc2[0:2], self.mesh, self.grid, self.settings.tilesize)
        if self.path_length(self.observation.loc, path1) < self.path_length(self.observation.loc, path2):
            return loc1[0:2]
        else:
            return loc2[0:2]
        
    def min_turn(self, location1, location2):
        dx1 = location1[0] - self.observation.loc[0]
        dy1 = location1[1] - self.observation.loc[1]
        turn1 = math.fabs(angle_fix(math.atan2(dy1, dx1) - self.observation.angle))
        
        dx2 = location2[0] - self.observation.loc[0]
        dy2 = location2[1] - self.observation.loc[1]
        turn2 = math.fabs(angle_fix(math.atan2(dy2, dx2) - self.observation.angle))            
        
        if (turn1 < turn2):
            return location1
        else:
            return location2
        
    def min_ammo_dist_fast(self, ammo_loc1, ammo_loc2):
        WEIGHT = self.__class__.AMMO_EXPECTATION_WEIGHT
        d1 = (point_dist(self.observation.loc, ammo_loc1) + WEIGHT / self.__class__.AMMOPACKS_LOC[ammo_loc1] )
        d2 = (point_dist(self.observation.loc, ammo_loc2) + WEIGHT / self.__class__.AMMOPACKS_LOC[ammo_loc2] )
        if (d1 < d2):
            #print "{0}<{1}".format(d1, d2)
            return ammo_loc1
        else:
            #print "{0}<{1}".format(d2, d1)
            return ammo_loc2
        
    def min_ammo_dist(self, ammo_loc1, ammo_loc2):
        WEIGHT = self.__class__.AMMO_EXPECTATION_WEIGHT
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
        
        # TODO: this function is unsafe. Replace with self.id == 0        
        
        if self.observation.step > self.__class__.LAST_ROUND:
            self.__class__.LAST_ROUND = self.observation.step
            return True
        else:
            self.__class__.LAST_ROUND = self.observation.step
            return False
        

    
    
