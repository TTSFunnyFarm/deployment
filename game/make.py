assert not __debug__  # Run with -OO

import argparse
import os
import sys

from cryptography.fernet import Fernet
from direct.directnotify import DirectNotifyGlobal


class FunnyFarmCompilerBase:
    notify = DirectNotifyGlobal.directNotify.newCategory('FunnyFarmCompilerBase')

    def __init__(self, version):
        self.version = version
        self.rootDir = os.getcwd()
        self.baseDir = os.path.join(self.rootDir, 'Toontowns-Funny-Farm')
        self.dataDir = os.path.join(self.rootDir, 'data')
        self.builtDir = os.path.join(self.rootDir, 'built')
        if not os.path.exists(self.builtDir):
            os.makedirs(self.builtDir)

    def encryptData(self, data):
        key = Fernet.generate_key()
        fernet = Fernet(key)
        data = key + fernet.encrypt(data)
        return data

    def generateGameData(self, configPath):
        configFile = os.path.join(self.baseDir, configPath)
        if not os.path.exists(configFile):
            return

        self.notify.info('Generating config data...')

        with open(configFile, 'r') as f:
            configData = f.read()
            f.close()

        configData = configData.replace('%GAME_VERSION%', self.version)
        configData = self.encryptData(configData.encode('utf-8'))
        gameData = 'CONFIG = %r\n' % configData
        with open(os.path.join(self.builtDir, 'gamedata.py'), 'w') as f:
            f.write(gameData)
            f.close()


parser = argparse.ArgumentParser(description='Build script for Toontown\'s Funny Farm')
parser.add_argument('--version', '-v', help='Game version')
parser.add_argument('--resources', '-r', help='Builds the game resources (phases).', action='store_true')
parser.add_argument('--game', '-g', help='Builds the game source code.', action='store_true')
parser.add_argument('--dist', '-d', help='Generate dist (patch manifest) files.', action='store_true')

args = parser.parse_args()

if sys.platform not in ('win32', 'darwin'):
    raise Exception('Platform not supported: %s' % sys.platform)

if (args.game or args.dist) and not args.version:
    raise Exception('Cannot build game or dist files without a game version. Use --version to set a game version.')

if (args.game or args.dist or args.resources):
    compiler = FunnyFarmCompilerBase(args.version)

if args.game:
    compiler.generateGameData(os.path.join('config', 'release.prc'))
