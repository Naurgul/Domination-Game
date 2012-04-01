from domination import core

MATCHES = 100
red = blu = 0

for i in range(MATCHES):
    settings = core.Settings(think_time = 0.0925, max_steps = 500)
    game = core.Game('agent_rulebased.py', 'agents/cereal3.py', rendered = False, settings = settings, verbose = False)
    game.run()
    s = game.stats.score
    if s > 0.55:
        red += 1
        teamWon = "red"
    elif s < 0.45:
        blu += 1
        teamWon = "blue"
    else:
        teamWon = "draw"
    
    print i+1, teamWon, game.stats.score_red, "-", game.stats.score_blue, "\n\t", red, "-", blu 

print "\nFinal score: ", red, "-", blu
