from panda3d.core import loadPrcFileData, Multifile, Filename
from cryptography.fernet import Fernet
import gamedata
import glob

# Config
key, prc = gamedata.CONFIG[0:45], gamedata.CONFIG[45:]
fernet = Fernet(key)
prc = fernet.decrypt(prc)
loadPrcFileData('game config', prc)
del key
del prc

# Resources
for file in glob.glob('resources/custom/*.mf'):
    mf = Multifile()
    mf.openReadWrite(Filename(file))
    names = mf.getSubfileNames()
    for name in names:
        ext = os.path.splitext(name)[1]
        if ext not in ['.jpg', '.jpeg', '.png', '.ogg', '.rgb']:
            mf.removeSubfile(name)

    vfs.mount(mf, Filename('resources'), 0)

# Time to shine, Funny Farm!
import toontown.toonbase.FunnyFarmStart
