from domination import core

settings = core.Settings(think_time = 0.625, max_steps=600)
drawGraphics = True
game = core.Game('agent_rulebased.py', 'agents/trooper.py', rendered = drawGraphics, settings = settings, verbose = True)
game.run()
