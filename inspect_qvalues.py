import pickle
pickle_file = open('qvalues.pickle', 'rb')
QVALUES = pickle.load(pickle_file)
pickle_file.close()
print QVALUES
