class Agent(object):
    
    NAME = "default_agent"
    SCOUT = None
    UNVISITED = None
    
    SPAWN_LOC = None
    AMMOPACKS_LOC = {}
    CPS_LOC = []
        
    def compare_spawn_dist(self, cp_loc):
        return (point_dist(self.__class__.SPAWN_LOC, cp_loc[0:2]))
    
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
        
        # shortcut for observations
        obs = self.observation
        
        # TODO: create a static variable to remember where the ammopacks are located on the map        
        # TODO: fill in roles for dead tanks
        # TODO: replace all distances with path lengths (or do ray traces at least)
        
        #save spawn area
        #this code only runs once, in the beginning of each match!
        if self.__class__.SPAWN_LOC is None:
            self.__class__.SPAWN_LOC = obs.loc
            self.__class__.CPS_LOC = obs.cps[:]
            self.__class__.CPS_LOC.sort(key = self.compare_spawn_dist)
            print "CPS_LOC: ", self.__class__.CPS_LOC
        
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
        self.whoIsScout(obs)   
        
        # decide behaviour based on role    
        if self.__class__.SCOUT == self.id:
            self.scoutBehaviour(ammopacks)
        else:            
            # TODO: if we pass close to an ammopack, we should get it
            
            # if I have no goal, then I start moving towards 
            # the CP closest to our spawn area that we don't own
            # TODO: take into account the number of enemies near the CP?
            self.nonScoutBehaviour()
        
                
        # if I see an enemy within range and I have ammo and there's no teammate between us,
        # shoot the motherfucker!         
        shoot = False
        if (obs.ammo > 0 and 
            obs.foes and 
            point_dist(obs.foes[0][0:2], obs.loc) < self.settings.max_range
            and not line_intersects_grid(obs.loc, obs.foes[0][0:2], self.grid, self.settings.tilesize)):            
            self.goal = obs.foes[0][0:2]
            shoot = True

        # use the mesh to find a path to my goal    
        if self.goal is None:
            print "no goal?"
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
        
        #print extra information when selected
        self.printInfo(obs, ammopacks)
        
        return (turn, speed, shoot)
    
    def updateAmmopacks(self, obs, ammopacks):
        
        # if I see an ammopack for the first time
        # add both that one and its symmetric to the list of ammopack locations
        for pack in ammopacks:
            #print "AMMOPACKS_X: ", pack        
            self.__class__.AMMOPACKS_LOC[(pack[0], pack[1])] = 20
            self.__class__.AMMOPACKS_LOC[(656 - pack[0], pack[1])] = 20 # 656 is the width of the screen in pixels
            #print "AMMOPACKS_LOC: {0}".format(self.__class__.AMMOPACKS_LOC)
        
        # for ammopacks that should be visible:
        #   t=20 if I see them
        #   t=0 if I don't see them
        # for ammopacks outside my range:
        #   increment t by 1
        
        for pack_loc in self.__class__.AMMOPACKS_LOC:
            if point_dist(pack_loc, obs.loc) < 100 :
                found = False
                for pack in ammopacks:
                    if pack[0:2] == pack_loc:
                        found = True
                if found:
                    self.__class__.AMMOPACKS_LOC[pack_loc] = 20
                else:
                    self.__class__.AMMOPACKS_LOC[pack_loc] = 1
            else:
                self.__class__.AMMOPACKS_LOC[pack_loc] = min( 20, self.__class__.AMMOPACKS_LOC[pack_loc] + 1 )
                
    def whoIsScout(self, obs):
        # if no one is scouting and I don't have ammo
        # TODO: even if I have no ammo, maybe I still have something better I should be doing
        if self.__class__.SCOUT == None and obs.ammo == 0:
            self.__class__.SCOUT = self.id     
            
        # If I am the scout and just found some ammo
        # then I stop being the scout
        if self.__class__.SCOUT == self.id and obs.ammo > 0:
            self.__class__.SCOUT = None
            self.goal = None       
        
    def nonScoutBehaviour(self):
        if self.goal is None:
            not_poss_cps = filter(lambda x: x[2] != self.team, self.observation.cps)
            
            if len(not_poss_cps) > 0:
                closest_cp = reduce(self.min_dist, not_poss_cps)
                print "Closest control point: ", closest_cp
                self.goal = closest_cp[0:2]
    
    def scoutBehaviour(self, ammopacks):  
                
        #print "MY LOCATION: ", obs.loc
        
        # if there is an ammopack close by
        # go get it
        if ammopacks: 
            #TODO: check path length or ray to make sure we're not going around walls
            closest_ammo = reduce(self.min_dist, ammopacks)
            #print "CLOSEST AMMO: ", closest_ammo
            self.goal = closest_ammo[0:2]
            print "Ammopack right ahead!"
        # else, check my list of ammopack locations and go towards the best one
        elif len(self.__class__.AMMOPACKS_LOC) > 0:
            best_ammo_loc = reduce(self.min_ammo_dist, self.__class__.AMMOPACKS_LOC)
            #print "{0}\t{1}".format(closest_ammo, self.__class__.AMMOPACKS_LOC)
            # go there if you think you have a good chance of finding ammo there
            if self.__class__.AMMOPACKS_LOC[best_ammo_loc] > 10:
                self.goal = best_ammo_loc
                print "There was an ammopack around here somewhere..."
            else:
                # if not, start exploring unvisited nodes    
                closest_node = reduce(self.min_dist, self.__class__.UNVISITED)
                self.goal = closest_node       
                print "Let's go exploring!"
            
    def printInfo(self, obs, ammopacks):
        if obs.selected:
            #print "Scouting: {0}".format(self.__class__.SCOUT == self.id) 
            #print "Goal: {0}".format(self.goal)
            #print "Visible ammo: {0}".format(ammopacks)
            #print "Ammo locations: {0}".format(self.__class__.AMMOPACKS_LOC)
            print "Ammo locations number: {0}".format(len(self.__class__.AMMOPACKS_LOC))

    
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
        
AS_STRING = """
class Agent(object):
 NAME="default_agent"
 def __init__(self,id,team,settings=None,field_rects=None,field_grid=None,nav_mesh=None):
  self.id=id
  self.team=team
  self.mesh=nav_mesh
  self.grid=field_grid
  self.settings=settings
  self.goal=None
  if id==0:
   self.all_agents=self.__class__.all_agents=[]
  self.all_agents.append(self)
 def observe(self,observation):
  self.observation=observation
  self.selected=observation.selected
 def action(self):
  obs=self.observation
  if self.goal is not None and point_dist(self.goal,obs.loc)<self.settings.tilesize:
   self.goal=None
  ammopacks=filter(lambda x:x[2]=="Ammo",obs.objects)
  if ammopacks:
   self.goal=ammopacks[0][0:2]
  if self.selected and self.observation.clicked:
   self.goal=self.observation.clicked
  if self.goal is None:
   self.goal=obs.cps[random.randint(0,len(obs.cps)-1)][0:2]
  shoot=False
  if(obs.ammo>0 and obs.foes and point_dist(obs.foes[0][0:2],obs.loc)<self.settings.max_range and not line_intersects_grid(obs.loc,obs.foes[0][0:2],self.grid,self.settings.tilesize)):
   self.goal=obs.foes[0][0:2]
   shoot=True
  path=find_path(obs.loc,self.goal,self.mesh,self.grid,self.settings.tilesize)
  if path:
   dx=path[0][0]-obs.loc[0]
   dy=path[0][1]-obs.loc[1]
   turn=angle_fix(math.atan2(dy,dx)-obs.angle)
   if turn>self.settings.max_turn or turn<-self.settings.max_turn:
    shoot=False
   speed=(dx**2+dy**2)**0.5
  else:
   turn=0
   speed=0
  return(turn,speed,shoot)
 def debug(self,surface):
  import pygame
  if self.id==0:
   surface.fill((0,0,0,0))
  if self.selected:
   if self.goal is not None:
    pygame.draw.line(surface,(0,0,0),self.observation.loc,self.goal)
 def finalize(self,interrupted=False):
  pass
"""