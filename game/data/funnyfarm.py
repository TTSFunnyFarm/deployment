from panda3d.core import loadPrcFileData
from cryptography.fernet import Fernet
import gamedata

# Config
key, prc = gamedata.CONFIG[0:45], gamedata.CONFIG[45:]
fernet = Fernet(key)
prc = fernet.decrypt(prc)
loadPrcFileData('game config', prc)
del fernet
del key
del prc

# Time to shine, Funny Farm!
import toontown.toonbase.FunnyFarmStart
