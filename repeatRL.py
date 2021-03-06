from domination import core

MATCHES = 20
red = blu = 0

for i in range(MATCHES):
    settings = core.Settings(think_time = 0.0925, max_steps=500)
    game = core.Game('agent_reinforcement_learning.py', 'agent_reinforcement_learning.py', rendered = False, settings = settings, verbose = False)
    game.run()
    s = game.stats.score
    if s > 0.55:
        red += 1
        print i+1, "\tred\t", red, "-", blu, "\t", game.stats.score_red, "-", game.stats.score_blue
    elif s < 0.45:
        blu += 1
        print i+1, "\tblue\t", red, "-", blu, "\t", game.stats.score_red, "-", game.stats.score_blue
    else:
        print i+1, "\tdraw\t", red, "-", blu, "\t", game.stats.score_red, "-", game.stats.score_blue

print "Final score: ", red, "-", blu
