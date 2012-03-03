from domination import core

settings = core.Settings(think_time = 0.0625, max_steps=200)
drawGraphics = True
game = core.Game('domination/agent.py', 'agent_reinforcement_learning.py', rendered = drawGraphics, settings = settings) #domination/agent.py
game.run()
