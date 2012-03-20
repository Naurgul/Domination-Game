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
    
    MAX_RECORDED_LOCATIONS = 5
    GOALS = []
    
    # ===== Constants =====
    
    EPSILON = 0.5
    FIRST_AGENT_ID = 0
    TEAM_SIZE = 6
    MAP_WIDTH = 656
    SHORT_DISTANCE = 30
    VERY_SHORT_DISTANCE = 10
    NUM_POINTS = 3
    NUM_AMMO_LOCS = 6
    AMMO_EXPECTATION_WEIGHT = 750
    EXPLORE_WAIT_STEPS = 50
    #MAX_AGENTS_PER_CP = 3
    
    # ===============
    

    def __init__(self, id, team, settings = None, field_rects = None, field_grid = None, nav_mesh = None):
        self.id = id
        self.team = team
        self.mesh = nav_mesh
        self.grid = field_grid
        self.settings = settings
        self.goal = None
        self.scout_goal = None
        
        self.PREVIOUS_AGENT_LOCATIONS = []
        self.RECORDED_LOCATIONS = 0
        self.IN_SPAWN_AREA = True
        
        self.__class__.UNVISITED = self.mesh.keys()
        
        if id == self.__class__.FIRST_AGENT_ID:
            self.all_agents = self.__class__.all_agents = []
        self.all_agents.append(self)

    
    def observe(self, observation):
        self.observation = observation
        self.selected = observation.selected
        
        in_spawn_area = False
        
        for loc in self.__class__.SPAWN_LOC:
            if point_dist(loc, observation.loc) < self.settings.tilesize:
                in_spawn_area = True
                break
            
        if in_spawn_area == True:
            print "Agent {0} is in the spawn area. Reinitializing...".format(self.id)
            self.PREVIOUS_AGENT_LOCATIONS = []
            self.RECORDED_LOCATIONS = 0
        
        # For each agent, record its previous MAX_RECORDED_LOCATIONS (x, y) positions        
                
        if self.RECORDED_LOCATIONS == self.__class__.MAX_RECORDED_LOCATIONS:
            self.RECORDED_LOCATIONS = 0
                    
        if len(self.PREVIOUS_AGENT_LOCATIONS) < self.__class__.MAX_RECORDED_LOCATIONS:
            self.PREVIOUS_AGENT_LOCATIONS.append(observation.loc)
        else:
            self.PREVIOUS_AGENT_LOCATIONS[self.RECORDED_LOCATIONS] = observation.loc
                
        #print "Recorded locations {0}: {1}".format(self.id, self.RECORDED_LOCATIONS)
        #print "Agent {0}, {1}: {2}".format(self.id, self.RECORDED_LOCATIONS, self.PREVIOUS_AGENT_LOCATIONS)
        self.RECORDED_LOCATIONS = self.RECORDED_LOCATIONS + 1
                
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
        
        # TODO LIST:
        #1. Do not overcrowd the same goals.
        #2. Do not get stuck on same team members.
        #3. Do not run around like idiots when spawncamping.
        #4. Do not hit your head to the walls.
        
        
        # shorthand for observations
        obs = self.observation
          
        #save spawn area
        #this code only runs once, in the beginning of each match!             
        
        if len(self.__class__.SPAWN_LOC) < self.__class__.TEAM_SIZE:
            self.__class__.SPAWN_LOC.append(obs.loc)
            
        # find the CPs we have and have not captured yet
        poss_cps = filter(lambda x: x[2] == self.team, self.observation.cps)
        not_poss_cps = filter(lambda x: x[2] != self.team, self.observation.cps)

        # find ammopacks within visual range
        ammopacks = filter(lambda x: x[2] == "Ammo", obs.objects)
        
        # compare visible ammopacks with the ones in memory
        #self.updateAmmopacks(obs, ammopacks)
        
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
        
        # see if there is an obvious easy goal close-by
        self.greedyGoal(ammopacks, obs, not_poss_cps)        
            
        # decide goal based on role
        if self.goal is None:    
            if self.id in self.__class__.SCOUTS:
                self.scoutBehaviour(ammopacks, obs, poss_cps, not_poss_cps)
            else:            
                self.trooperBehaviour(obs, ammopacks, poss_cps, not_poss_cps)       
            
        #print extra information when selected
        self.printInfo(obs, ammopacks)
        
        # return specific (low-level) actions given the goal
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
        if self.id == 0:
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
        
        MAX_SCOUTS = self.__class__.TEAM_SIZE / (len(not_poss_cps) + 1)
        #print MAX_SCOUTS
        # if no one is scouting and I don't have ammo
        # and I am not too close to my goal (unless I have no goal)
        # TODO: Sort by distance to goal and pick the one who is the farthest!
        if len(self.__class__.SCOUTS) < MAX_SCOUTS and obs.ammo == 0 and ( self.goal is None or point_dist(obs.loc, self.goal) > self.__class__.SHORT_DISTANCE ):
            self.__class__.SCOUTS.append(self.id)     
            
        # If I am the scout and just found some ammo
        # then I stop being the scout
        if self.id in self.__class__.SCOUTS and obs.ammo > 0:
            self.__class__.SCOUTS.remove(self.id)
            self.goal = None
            
    def greedyGoal(self, ammopacks, obs, not_poss_cps):
        
        # if there is an ammopack close by
        # with no one else to get it
        # go get it        
        if ammopacks:
            bestpack = self.getBestTarget(ammopacks, obs) 
            if bestpack is not None:
                self.goal = bestpack[0:2]
                #print "Ammopack right ahead!"
           
        # if there is a cp nearby
        # with no one else to get it
        # go get it
        if self.goal is None:
            cps_close = filter(lambda x: point_dist(x, obs.loc) < self.settings.max_see, not_poss_cps)
            bestcps = self.getBestTarget(cps_close, obs) 
            if bestcps is not None:
                self.goal = bestcps[0:2]
        
        
    def trooperBehaviour(self, obs, ammopacks, poss_cps, not_poss_cps):
        
        # TODO: Same situation, if we have ammo, set goal to enemy        
        # TODO: Change goal if too many agents have the same goal as you do 
        
        # remove goal if it is a CP we already control
        if self.goal is not None and self.goal not in map(lambda x: x[0:2], not_poss_cps):
            self.goal = None            
            
        # If enemy is nearest to CP we own, start going back to defend/recapture
        for cp in poss_cps:
            if self.goal is None or point_dist(obs.loc, cp[0:2]) < point_dist(obs.loc, self.goal):
                allteam = obs.friends[:]
                allteam.append(obs.loc)
                if self.whoIsTheClosest(allteam, cp[0:2]) == obs.loc:
                    for foe in obs.foes:
                        if point_dist(foe, cp[0:2]) < point_dist(obs.loc, cp[0:2]) and not cp[0:2] in self.__class__.GOALS:
                            self.goal = cp[0:2]

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
                
       
                
    
    def scoutBehaviour(self, ammopacks, obs, poss_cps, not_poss_cps):  
                
    
                        
        # check my list of ammopack locations and go towards the best one
        if self.goal is None and len(self.__class__.AMMOPACKS_LOC) > 0:
            #only check unseen ammo locations, the rest are handled by the greedy goal tihng
            unseen_ammo_locs = filter(lambda loc: point_dist(loc, obs.loc) > self.__class__.SHORT_DISTANCE, self.__class__.AMMOPACKS_LOC)
            best_ammo_loc = reduce(self.min_ammo_dist, unseen_ammo_locs)
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
            self.trooperBehaviour(obs, ammopacks, poss_cps, not_poss_cps)
            
            
    def GoalToAction(self, obs):
        
        # TODO: Jiggle around if you're not going anywhere
        
        # if I see an enemy within range and I have ammo 
        # there's no wall or friendly between us,
        # shoot the motherfucker!  
        shoot = False
        
        if obs.ammo > 0:
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
            
            # TODO: Fix agents running with top speed when they should be rotating in place.
            # if moving would get us away from our goal, turn in place 
            # actually, don't do it! it's dangerous
            # TODO: Unless you have an enemy on your tail!
            #if turn < math.pi / 2:
            #    speed = (dx**2 + dy**2)**0.5
            #else:
            #    speed = 0                
            speed = (dx**2 + dy**2)**0.5
            
        else:
            turn = 0
            speed = 0
            
        # If the agent hasn't changed its position for MAX_RECORDED_LOCATIONS
        # rounds and it is not in the respawn area, there is a high probability
        # that it got stuck somewhere. In that case, try to escape.
                                
        if len(self.PREVIOUS_AGENT_LOCATIONS) > 1:
            agent_changed_location = False
            first_loc = self.PREVIOUS_AGENT_LOCATIONS[0]

            for loc in self.PREVIOUS_AGENT_LOCATIONS:
                if point_dist(loc, first_loc) > self.settings.tilesize:
                    agent_changed_location = True
                    break
                        
            if agent_changed_location == False:
                print "Agent {0} hasn't changed location".format(self.id)
                turn = self.settings.max_turn
                speed = math.floor(self.settings.max_speed / 4)
                #self.PREVIOUS_AGENT_LOCATIONS = []
                #self.RECORED_LOCATIONS = 0
            
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

    def getBestTarget(self, targets, obs):
        everyone = obs.friends + obs.foes
        everyone.append(obs.loc)
        #print everyone
        unobstracted_targets = filter(lambda t: not line_intersects_grid(obs.loc, t[0:2], self.grid, self.settings.tilesize), targets)
        good_targets = filter(lambda t: self.whoIsTheClosest(everyone, t) == obs.loc, unobstracted_targets)
        if len(good_targets) > 0:
            return reduce(self.min_dist, good_targets)
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