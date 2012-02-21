import pickle
from domination import core
rp = pickle.load(open('data\\replays\\empire_v2.pickle','rb'))
rp.play()