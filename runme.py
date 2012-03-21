from domination import core

settings = core.Settings(think_time = 0.625, max_steps=600)
drawGraphics = True
game = core.Game('agent_rulebased_4.py', 'agent_rulebased_5.py', rendered = drawGraphics, settings = settings, verbose = True)
game.run()
