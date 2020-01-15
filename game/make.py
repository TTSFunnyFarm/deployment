assert not __debug__  # Run with -OO

from cryptography.fernet import Fernet
from direct.directnotify import DirectNotifyGlobal
import argparse
import os
import shutil
import subprocess
import sys

parser = argparse.ArgumentParser(description='Build script for Toontown\'s Funny Farm')
parser.add_argument('--version', '-v', help='Game version')
parser.add_argument('--resources', '-r', help='Builds the game resources (phases).', action='store_true')
parser.add_argument('--game', '-g', help='Builds the game source code.', action='store_true')
parser.add_argument('--dist', '-d', help='Generate dist (patch manifest) files.', action='store_true')
#if sys.platform == 'win32':
#    parser.add_argument('--arch', '-a', help='Target architecture', choices=['win32', 'win64'], required=True)

args = parser.parse_args()

notify = DirectNotifyGlobal.directNotify.newCategory('FunnyFarmMake')
notify.setInfo(True)

if sys.platform not in ('win32', 'darwin'):
    notify.error('Platform not supported: %s' % sys.platform)

if (args.game or args.dist) and not args.version:
    notify.error('Cannot build game or dist files without a game version. Use --version to set a game version.')

ROOT_DIR = os.getcwd()
BUILT_DIR = 'built'
DATA_DIR = 'data'
FUNNY_FARM_SRC_DIR = 'Toontowns-Funny-Farm'
PANDA3D_DIR = os.path.abspath(os.path.join(os.path.dirname(sys.executable), '..'))

if not os.path.exists(BUILT_DIR):
    os.makedirs(BUILT_DIR)

def getFileContents(filename, encrypt=False):
    with open(filename, 'rb') as f:
        data = f.read()

    if encrypt:
        key = Fernet.generate_key()
        fernet = Fernet(key)
        data = key + fernet.encrypt(data)

    return data

def generateGameData():
    configFile = os.path.join(BUILT_DIR, 'config', 'release.prc')
    if not os.path.exists(configFile):
        return

    notify.info('Generating config data...')

    with open(configFile, 'r') as f:
        configData = f.read()

    configData = configData.replace('%GAME_VERSION%', args.version)
    with open(configFile, 'w') as f:
        f.write(configData)

    config = getFileContents(configFile, True)
    gameData = 'CONFIG = %r\n' % config
    with open(os.path.join(BUILT_DIR, 'gamedata.py'), 'w') as f:
        f.write(gameData)
        f.close()

def copyBuildFiles():
    if os.path.exists(BUILT_DIR):
        notify.info('Cleaning up old build files...')
        for root, _, __ in os.walk(BUILT_DIR):
            if root == 'built' or 'funnyfarm.build' in root:
                continue

            shutil.rmtree(root)

    notify.info('Copying build files...')
    if not os.path.exists(FUNNY_FARM_SRC_DIR):
        return

    libotp = os.path.join(FUNNY_FARM_SRC_DIR, 'libotp')
    if not os.path.exists(libotp):
        return

    otpDir = os.path.join(FUNNY_FARM_SRC_DIR, 'otp')
    if not os.path.exists(otpDir):
        return

    toontownDir = os.path.join(FUNNY_FARM_SRC_DIR, 'toontown')
    if not os.path.exists(toontownDir):
        return

    shutil.copytree(libotp, os.path.join(BUILT_DIR, 'libotp'))
    shutil.copytree(otpDir, os.path.join(BUILT_DIR, 'otp'))
    shutil.copytree(toontownDir, os.path.join(BUILT_DIR, 'toontown'))

    configFile = os.path.join(FUNNY_FARM_SRC_DIR, 'config', 'release.prc')
    if not os.path.exists(configFile):
        return

    buildConfigFile = os.path.join(BUILT_DIR, 'config', 'release.prc')
    if not os.path.exists(os.path.dirname(buildConfigFile)):
        os.makedirs(os.path.dirname(buildConfigFile))

    shutil.copy(configFile, os.path.join(BUILT_DIR, 'config'))

    if not os.path.exists(DATA_DIR):
        return

    mainFile = os.path.join(DATA_DIR, 'funnyfarm.py')
    if not os.path.exists(mainFile):
        return

    shutil.copy(mainFile, BUILT_DIR)

def buildGame():
    notify.info('Building the game...')
    try:
        import nuitka
    except:
        raise ModuleNotFoundError('Nuitka was not found! Please install Nuitka via pip.')

    os.chdir(BUILT_DIR)
    returnCode = subprocess.check_call([sys.executable, '-OO', '-m', 'nuitka', '--standalone', '--file-reference-choice=frozen', '--show-progress', '--show-scons', '--follow-imports', '--python-flag=-S,-OO', 'funnyfarm.py'])
    if returnCode == 0:
        notify.info('Build finished successfully!')

def buildResources():
    notify.info('Building the resources...')
    os.chdir(os.path.join(ROOT_DIR, FUNNY_FARM_SRC_DIR, 'resources'))
    destDir = os.path.join(ROOT_DIR, BUILT_DIR, 'resources')
    if not os.path.exists(destDir):
        os.makedirs(destDir)

    for phase in os.listdir('.'):
        if not phase.startswith('phase_'):
            continue

        if not os.path.isdir(phase):
            continue

        filename = phase + '.mf'
        filepath = os.path.join(destDir, filename)
        returnCode = subprocess.check_call([os.path.join(PANDA3D_DIR, 'bin', 'multify'), '-c', '-f', filepath, phase])
        if returnCode == 0:
            notify.info('%s built successfully!' % phase)

    notify.info('All resources built successfully!')

def copyRequiredGameFiles():
    notify.info('Copying required game files...')
    os.chdir(ROOT_DIR)
    if not os.path.exists(PANDA3D_DIR):
        return

    pandaDlls = [
        'libpandagl.dll',
        'libp3windisplay.dll',
        'cgGL.dll',
        'libp3openal_audio.dll'
    ]

    for pandaDll in pandaDlls:
        shutil.copy(os.path.join(PANDA3D_DIR, 'bin', pandaDll), os.path.join(BUILT_DIR, 'funnyfarm.dist'))

    notify.info('Done!')


def copyRequiredResourceFiles():
    notify.info('Copying required game files...')
    os.chdir(ROOT_DIR)
    resourcesDir = os.path.join(BUILT_DIR, 'resources')
    builtResourcesDir = os.path.join(BUILT_DIR, 'funnyfarm.dist', 'resources')
    if not os.path.exists(builtResourcesDir):
        os.makedirs(builtResourcesDir)

    phases = [phase for phase in os.listdir(resourcesDir) if phase.startswith('phase_') and phase.endswith('.mf')]
    for phase in phases:
        shutil.copy(os.path.join(resourcesDir, phase), builtResourcesDir)


if args.game:
    copyBuildFiles()
    generateGameData()
    buildGame()
    copyRequiredGameFiles()

if args.resources:
    buildResources()
    copyRequiredResourceFiles()
