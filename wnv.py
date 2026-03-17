def createMosquito():
    return {
        'infected': False
    }
def createBird():
    return {
        'infected': False,
        'dead': False
    }
def createHuman():
    return {
        'infected': False,
        'dead': False
    }

def biteCheck(host, victim):
    if (host['infected']):
        #add percentage here
        victim['infected'] = True
    return victim

m = createMosquito()
h = createHuman()
print(h['infected'])
m['infected'] = True
h = biteCheck(h, m)
print(h['infected'])
