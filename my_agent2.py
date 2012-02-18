class Agent(object):
    
    NAME = "default_agent"
    SCOUT = None
    UNVISITED = None
    
    SPAWN_LOC = None
    AMMOPACKS_LOC = []
    CPS_LOC = []
    
    def compare_ammo_dist(self, ammo_loc):
        return (point_dist(self.__class__.SPAWN_LOC, ammo_loc[0:2]) / ammo_loc[2] )
    
    def min_dist(self, loc1, loc2):
        if point_dist(self.observation.loc, loc1[0:2]) < point_dist(self.observation.loc, loc2[0:2]):
            return loc1[0:2]
        else:
            return loc2[0:2]
    
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
        obs = self.observation
        
        # TODO: create a static variable to remember where the ammopacks are located on the map        
        # TODO: fill in roles for dead tanks
        
        ammopacks = filter(lambda x: x[2] == "Ammo", obs.objects)
        self.updateAmmopacks(obs, ammopacks)
        
        if self.__class__.SPAWN_LOC is None:
            self.__class__.SPAWN_LOC = obs.loc
            self.__class__.CPS_LOC = obs.cps[:]
            self.__class__.CPS_LOC.sort(key = self.compare_dist)
            #print "CPS SORTED: ", self.__class__.CPS_LOC
        
        if obs.selected:
            print "SCOUT id: ", self.__class__.SCOUT
            print "SELF ID: ", self.id
            print "CONTROL: ", obs.cps
        
        if self.goal is not None and point_dist(self.goal, obs.loc) < self.settings.tilesize:
            self.goal = None
                        
        for x in self.__class__.UNVISITED:
            if point_dist(obs.loc, x) < self.settings.tilesize:
                self.__class__.UNVISITED.remove(x)
        
        if self.__class__.SCOUT == None and obs.ammo == 0:
            self.__class__.SCOUT = self.id
                        
        if self.__class__.SCOUT == self.id and obs.ammo > 0:
            self.__class__.SCOUT = None
            self.goal = None        
            
        shoot = False
            
        if self.__class__.SCOUT == self.id:
            self.scoutBehaviour(ammopacks)
        else:
            
            # TODO: if we pass close to an ammopack, we should get it
            
            if self.goal is None:
                not_poss_cps = filter(lambda x: x[2] != self.team, obs.cps)
                not_poss_len = len(not_poss_cps)
                
                #cps_id = divmod(self.id, 2)
                cps_id = 0
                self.goal = obs.cps[cps_id][0:2]
            
            if (obs.ammo > 0 and 
                obs.foes and 
                point_dist(obs.foes[0][0:2], obs.loc) < self.settings.max_range
                and not line_intersects_grid(obs.loc, obs.foes[0][0:2], self.grid, self.settings.tilesize)):
                
                self.goal = obs.foes[0][0:2]
                shoot = True            
            
        path = find_path(obs.loc, self.goal, self.mesh, self.grid, self.settings.tilesize)
        
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
    
    def updateAmmopacks(self, obs, ammopacks):
        #for ammopacks that should be visible:
        #   t=20 if I see them
        #   t=0 if I don't see them
        #for ammopacks outside my range:
        #   increment t by 1
        
        for pack_loc in self.__class__.AMMOPACKS_LOC:
            if point_dist(pack_loc[0:2], obs.loc) < 100:
                found = False
                for pack in ammopacks:
                    if pack[0:2] == pack_loc[0:2]:
                        found = True
                if found:
                    pack_loc = (pack_loc[0], pack_loc[1], 20)
                else:
                    pack_loc = (pack_loc[0], pack_loc[1], 0)
            else:
                pack_loc = (pack_loc[0], pack_loc[1], min(20, pack_loc[2] + 1))
                
            
        
    
    def scoutBehaviour(self, ammopacks):
        
                    
        for pack in ammopacks:
            print "AMMOPACKS_X: ", pack
            if pack[0:2] not in self.__class__.AMMOPACKS_LOC:
                self.__class__.AMMOPACKS_LOC.append((pack[0], pack[1], 20))
                self.__class__.AMMOPACKS_LOC.append((656 - pack[0], pack[1], 20))
                print "AMMOPACKS_LOC: ", self.__class__.AMMOPACKS_LOC
                
        #print "MY LOCATION: ", obs.loc
        
        if ammopacks: 
            #TODO: check path length or ray to make sure we're not going around walls
            closest_ammo = reduce(self.min_dist, ammopacks)
            #print "CLOSEST AMMO: ", closest_ammo
            self.goal = closest_ammo[0:2]
        elif len(self.__class__.AMMOPACKS_LOC) > 0:
            closest_ammo = reduce(self.min_dist, self.__class__.AMMOPACKS_LOC)
            self.goal = closest_ammo
        else:
            closest_node = reduce(self.min_dist, self.__class__.UNVISITED)
            self.goal = closest_node        
        
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