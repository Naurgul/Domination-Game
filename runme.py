from domination import core

settings = core.Settings(think_time = 0.0625, max_steps=600)
drawGraphics = True
game = core.Game('old.py', 'agent_rulebased.py', rendered = drawGraphics, settings = settings, verbose = True)
game.run()
