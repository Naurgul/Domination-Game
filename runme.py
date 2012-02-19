from domination import core

settings = core.Settings(think_time = 0.0625)
drawGraphics = True
game = core.Game('my_agent2.py', 'domination/agent.py',  rendered = drawGraphics, settings = settings)
game.run()