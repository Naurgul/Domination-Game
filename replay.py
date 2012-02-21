import pickle
from domination import core
rp = pickle.load(open('replay.pickle','rb'))
rp.play()