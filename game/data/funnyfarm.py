from panda3d.core import loadPrcFileData, Multifile
from cryptography.fernet import Fernet
import gamedata
import glob

# Config
configKey = gamedata.CONFIG[0:45]
configData = gamedata.CONFIG[45:]
configFernet = Fernet(configKey)
config = configFernet.decrypt(configData)
loadPrcFileData('game config', config.decode())

# Resources
for file in glob.glob('resources/*.mf'):
    mf = Multifile()
    mf.openReadWrite(Filename(file))
    names = mf.getSubfileNames()
    for name in names:
        ext = os.path.splitext(name)[1]
        if ext not in ['.jpg', '.jpeg', '.png', '.ogg', '.rgb']:
            mf.removeSubfile(name)

    vfs.mount(mf, Filename('/'), 0)

# Time to shine, Funny Farm!
import toontown.toonbase.FunnyFarmStart
