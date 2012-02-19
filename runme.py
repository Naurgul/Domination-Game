from domination import core

settings = core.Settings(think_time = 0.0625, max_steps=200)
drawGraphics = False
game = core.Game('domination/agent.py', 'excrucian.py', rendered = drawGraphics, settings = settings)
game.run()