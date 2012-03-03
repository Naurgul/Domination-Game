from domination import core

MATCHES = 100
red = blu = 0

for i in range(MATCHES):
    settings = core.Settings(think_time = 0.0625, max_steps=600)
    game = core.Game('old2.py', 'agent_rulebased.py', rendered = False, settings = settings, verbose = False)
    game.run()
    s = game.stats.score
    if s > 0.55:
        red += 1
        print i+1, "\tred\t", red, "-", blu
    elif s < 0.45:
        blu += 1
        print i+1, "\tblue\t", red, "-", blu
    else:
        print i+1, "\tdraw\t", red, "-", blu

print "Final score: ", red, "-", blu
    

