from cryptography.fernet import Fernet
from direct.directnotify import DirectNotifyGlobal
import argparse
import codecs
import os
import shutil
import subprocess
import sys

parser = argparse.ArgumentParser(description='Build script for Toontown\'s Funny Farm')
parser.add_argument('--version', help='Game version', required=True)
args = parser.parse_args()

notify = DirectNotifyGlobal.directNotify.newCategory('FunnyFarmMake')
notify.setInfo(True)

FUNNY_FARM_SRC_DIR = 'Toontowns-Funny-Farm'
BUILT_DIR = 'built'
DATA_DIR = 'data'

if not os.path.exists(BUILT_DIR):
    os.makedirs(BUILT_DIR)

def generateKey(size=256):
    return os.urandom(size)

def getFileContents(filename, encrypt=False):
    with open(filename, 'rb') as f:
        data = f.read()

    if encrypt:
        key = generateKey(32)
        key = codecs.encode(key, 'base64')
        fernet = Fernet(key)
        data = key + fernet.encrypt(data)

    return data

def generateGameData():
    configFile = BUILT_DIR + '/config/release.prc'
    if not os.path.exists(configFile):
        return

    notify.info('Generating config data...')
    
    with open(configFile, 'r') as f:
        configData = f.read()

    configData.replace('%GAME_VERSION%', args.version)
    with open(configFile, 'w') as f:
        f.write(configData)

    config = getFileContents(configFile, True)
    gameData = 'CONFIG = %r\n' % config
    with open(BUILT_DIR + '/gamedata.py', 'w') as f:
        f.write(gameData)
        f.close()

def copyBuildFiles():
    if os.path.exists(BUILT_DIR):
        notify.info('Cleaning up old build files...')
        shutil.rmtree(BUILT_DIR)

    notify.info('Copying build files...')
    if not os.path.exists(FUNNY_FARM_SRC_DIR):
        return

    otpDir = FUNNY_FARM_SRC_DIR + '/otp'
    if not os.path.exists(otpDir):
        return

    toontownDir = FUNNY_FARM_SRC_DIR + '/toontown'
    if not os.path.exists(toontownDir):
        return

    shutil.copytree(otpDir, BUILT_DIR + '/otp')
    shutil.copytree(toontownDir, BUILT_DIR + '/toontown')

    configFile = FUNNY_FARM_SRC_DIR + '/config/release.prc'
    if not os.path.exists(configFile):
        return

    buildConfigFile = BUILT_DIR + '/config/release.prc'
    if not os.path.exists(os.path.dirname(buildConfigFile)):
        os.makedirs(os.path.dirname(buildConfigFile))

    shutil.copy(configFile, BUILT_DIR + '/config/release.prc')

    if not os.path.exists(DATA_DIR):
        return

    mainFile = DATA_DIR + '/funnyfarm.py'
    if not os.path.exists(mainFile):
        return

    shutil.copy(mainFile, BUILT_DIR + '/funnyfarm.py')

def buildGame():
    notify.info('Building the game...')
    try:
        import nuitka
    except:
        raise ModuleNotFoundError('Nuitka was not found! Please install Nuitka via pip.')

    try:
        import clcache
    except:
        raise ModuleNotFoundError('clcache was not found! Please install clcache via pip.')

    os.chdir(BUILT_DIR)
    pythonDir = os.path.dirname(sys.executable)
    scriptsDir = os.path.join(pythonDir, 'Scripts/clcache.exe')
    os.environ['NUITKA_CLCACHE_BINARY'] = scriptsDir
    returnCode = subprocess.check_call([sys.executable, '-m', 'nuitka', '--standalone', '--show-progress', '--show-scons', '--follow-imports', '--python-flag=-OO', 'funnyfarm.py'])
    if returnCode == 0:
        notify.info('Build finished successfully!')


copyBuildFiles()
generateGameData()
buildGame()
