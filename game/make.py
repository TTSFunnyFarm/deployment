assert not __debug__  # Run with -OO

import argparse
import os
import shutil
import subprocess
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
        self.workingDir = os.path.join(self.rootDir, 'builds', self.version)
        if not os.path.exists(self.workingDir):
            os.makedirs(self.workingDir)

        self.panda3dDir = None
        self.sourceDirs = []
        self.mainFile = None

    def addSourceDir(self, sourceDir):
        if sourceDir not in self.sourceDirs:
            self.sourceDirs.append(sourceDir)

    def setMainFile(self, mainFile):
        self.mainFile = mainFile

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
        with open(os.path.join(self.workingDir, 'gamedata.py'), 'w') as f:
            f.write(gameData)
            f.close()

    def removeOldBuildFiles(self):
        if os.path.exists(self.workingDir):
            self.notify.info('Cleaning up old build files...')
            for item in os.listdir(self.workingDir):
                if item == 'built':
                    continue

                itemPath = os.path.join(self.workingDir, item)
                if os.path.isdir(itemPath):
                    shutil.rmtree(itemPath)
                else:
                    os.remove(itemPath)

    def copyBuildFiles(self):
        self.removeOldBuildFiles()
        self.notify.info('Copying build files...')
        for sourceDir in self.sourceDirs:
            filepath = os.path.join(self.baseDir, sourceDir)
            if not os.path.exists(filepath):
                continue

            shutil.copytree(filepath, os.path.join(self.workingDir, sourceDir))

        if os.path.exists(self.mainFile):
            shutil.copy(self.mainFile, self.workingDir)

    def buildGame(self):
        self.notify.info('Building the game...')
        try:
            import nuitka
        except:
            raise ModuleNotFoundError('Nuitka was not found! Please install Nuitka via pip.')

        returnCode = subprocess.check_call([sys.executable, '-OO', '-m', 'nuitka', '--standalone', '--file-reference-choice=frozen', '--show-progress', '--show-scons', '--follow-imports', '--python-flag=-S,-OO', '%s' % self.mainFile], cwd=self.workingDir)
        if returnCode == 0:
            self.notify.info('Build finished successfully!')

    def buildResources(self):
        if not self.panda3dDir:
            self.notify.error('Panda3D directory not set! Unable to build resources.')

        if not os.path.exists(self.panda3dDir):
            return

        self.notify.info('Building the resources...')
        destDir = os.path.join(self.rootDir, self.workingDir, 'built', 'resources')
        if not os.path.exists(destDir):
            os.makedirs(destDir)

        resourcesDir = os.path.join(self.baseDir, 'resources')
        for phase in os.listdir(resourcesDir):
            if not phase.startswith('phase_'):
                continue

            phasePath = os.path.join(resourcesDir, phase)
            if not os.path.isdir(phasePath):
                continue

            filename = phase + '.mf'
            filepath = os.path.join(destDir, filename)
            returnCode = subprocess.check_call([os.path.join(self.panda3dDir, 'bin', 'multify'), '-c', '-f', filepath, phasePath])
            if returnCode == 0:
                self.notify.info('%s built successfully!' % phase)

        self.notify.info('All resources built successfully!')

    def copyRequiredGameFiles(self):
        # This is entirely platform dependent and must be overriden by subclass.
        raise NotImplementedError('copyRequiredGameFiles')


class FunnyFarmCompilerWindows(FunnyFarmCompilerBase):
    notify = DirectNotifyGlobal.directNotify.newCategory('FunnyFarmCompilerWindows')

    def __init__(self, version):
        FunnyFarmCompilerBase.__init__(self, version)
        self.panda3dDir = os.path.abspath(os.path.join(os.path.dirname(sys.executable), '..'))


class FunnyFarmCompilerDarwin(FunnyFarmCompilerBase):
    notify = DirectNotifyGlobal.directNotify.newCategory('FunnyFarmCompilerDarwin')

    def __init__(self, version):
        FunnyFarmCompilerBase.__init__(self, version)
        self.panda3dDir = os.path.join(self.rootDir, 'funny-farm-panda3d', 'built_dev')


parser = argparse.ArgumentParser(description='Build script for Toontown\'s Funny Farm')
parser.add_argument('--version', '-v', help='Game version', required=True)
parser.add_argument('--resources', '-r', help='Builds the game resources (phases).', action='store_true')
parser.add_argument('--game', '-g', help='Builds the game source code.', action='store_true')
parser.add_argument('--dist', '-d', help='Generate dist (patch manifest) files.', action='store_true')

args = parser.parse_args()

if sys.platform not in ('win32', 'darwin'):
    raise Exception('Platform not supported: %s' % sys.platform)

if (args.game or args.dist or args.resources):
    if sys.platform == 'win32':
        compiler = FunnyFarmCompilerWindows(args.version)
    elif sys.platform == 'darwin':
        compiler = FunnyFarmCompilerDarwin(args.version)

if args.game:
    compiler.generateGameData(os.path.join('config', 'release.prc'))
    compiler.addSourceDir('libotp')
    compiler.addSourceDir('otp')
    compiler.addSourceDir('toontown')
    compiler.setMainFile(os.path.join(compiler.dataDir, 'funnyfarm.py'))
    compiler.copyBuildFiles()
    compiler.buildGame()
    compiler.copyRequiredGameFiles()

if args.resources:
    compiler.buildResources()
