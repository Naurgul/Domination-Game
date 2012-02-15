class Agent(object):
    
    NAME = "default_agent"
    SCOUT = None
    UNVISITED = None
    
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
        
        # TODO: if I am the scout and I reached my goal and my goal is to visit the nodes, I should
        # remove the visited node from the list
        
        if self.goal is not None and point_dist(self.goal, obs.loc) < self.settings.tilesize:
            if self.__class__.SCOUT == self.id:
                
                if obs.ammo > 0:
                    self.__class__.SCOUT = None
                
                if point_dist(obs.loc, self.scout_goal) < self.settings.tilesize:
                    self.__class__.UNVISITED.remove(self.goal)
                    self.scout_goal = None
                    
            self.goal = None
        
        if self.__class__.SCOUT == None and obs.ammo == 0:
            self.__class__.SCOUT = self.id
            
        if self.__class__.SCOUT == self.id:
            ammopacks = filter(lambda x: x[2] == "Ammo", obs.objects)
            
            if ammopacks:
                closest_ammo = reduce(self.min_dist, ammopacks)
                self.goal = closest_ammo[0:2]
            else:
                closest_node = reduce(self.min_dist, self.__class__.UNVISITED)
                self.self.__class__.scout_goal = closest_node
                self.goal = closest_node
        else:
            #closest_cp = reduce(self.min_dist, obs.cps)
            #self.goal = closest_cp
            if self.goal is None:
                self.goal = obs.cps[random.randint(0,len(obs.cps)-1)][0:2]
                    
            # Shoot enemies
            shoot = False
            if (obs.ammo > 0 and 
                obs.foes and 
                point_dist(obs.foes[0][0:2], obs.loc) < self.settings.max_range
                and not line_intersects_grid(obs.loc, obs.foes[0][0:2], self.grid, self.settings.tilesize)):
                
                self.goal = obs.foes[0][0:2]
                shoot = True            
            
        # print self.mesh
        # if self.__class__.SCOUTING_ID == self.id:
            
        
        #if self.goal is None:
            #not_poss_cps = filter(lambda x: x[2] != self.team, obs.cps)
            #min_dist_cp = point_dist(obs.loc, not_poss_cps[0][0:2])
            #closest_cp = not_poss_cps[0][0:2]
            
            #for x in not_poss_cps:
                #if point_dist(obs.loc, x[0:2]) < min_dist_cp:
                        #min_dist_cp = point_dist(obs.loc, x[0:2])
                        #closest_cp = x[0:2]
            
            #self.goal = closest_cp           
            #ammopacks = filter(lambda x: x[2] == "Ammo", obs.objects)
            
            #if ammopacks:
                #min_dist_ammo = point_dist(obs.loc, ammopacks[0][0:2])
                #closest_ammo = ammopacks[0][0:2]
                        
                #for x in ammopacks:
                    #if point_dist(obs.loc, x[0:2]) < min_dist_ammo:
                        #min_dist_ammo = point_dist(obs.loc, x[0:2])
                        #closest_ammo = x[0:2]
            
                #if min_dist_ammo < min_dist_cp:
                    #self.goal = closest_ammo
        
        ## Shoot enemies
        
        #shoot = False
        
        #if (obs.ammo > 0 and obs.foes and 
            #point_dist(obs.foes[0][0:2], obs.loc) < self.settings.max_range and not
            #line_intersects_grid(obs.loc, obs.foes[0][0:2], self.grid, self.settings.tilesize)):
            #self.goal = obs.foes[0][0:2]
            #shoot = True

        # Compute path, angle and drive
        
        shoot = False
        #print "Agent's goal: ", self.goal
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