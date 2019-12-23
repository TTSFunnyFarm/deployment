from panda3d.core import loadPrcFileData
from cryptography.fernet import Fernet
import gamedata

configKey = gamedata.CONFIG[0:45]
configData = gamedata.CONFIG[45:]

configFernet = Fernet(configKey)
config = configFernet.decrypt(configData)

loadPrcFileData('game config', config.decode())

import toontown.toonbase.FunnyFarmStart
