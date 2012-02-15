from domination import core

settings = core.Settings(think_time = 0.0625)
game = core.Game('my_agent.py', 'domination/agent.py', rendered = True, settings = settings)
game.run()