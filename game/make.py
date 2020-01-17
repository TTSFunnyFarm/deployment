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
        self.builtDir = None
        self.panda3dDevDir = os.path.join(self.rootDir, 'funny-farm-panda3d', 'built_dev')
        self.panda3dProdDir = None
        self.sourceDirs = []
        self.mainFile = None
        self.configFile = None

    def addSourceDir(self, sourceDir):
        if sourceDir not in self.sourceDirs:
            self.sourceDirs.append(sourceDir)

    def setMainFile(self, mainFile):
        self.mainFile = mainFile

    def setConfigFile(self, configFile):
        self.configFile = configFile

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

    def buildGame(self):
        self.notify.info('Building the game...')
        try:
            import nuitka
        except:
            raise ModuleNotFoundError('Nuitka was not found! Please install Nuitka via pip.')

        returnCode = subprocess.check_call([sys.executable, '-OO', '-m', 'nuitka', '--standalone', '--file-reference-choice=frozen', '--show-progress', '--show-scons', '--follow-imports', '--python-flag=-S,-OO', '%s' % os.path.basename(self.mainFile)], cwd=self.workingDir)
        if returnCode == 0:
            self.notify.info('Build finished successfully!')

    def copyToBuiltDir(self):
        # This is entirely platform dependent and must be overriden by subclass.
        raise NotImplementedError('copyToBuiltDir')

    def buildResources(self):
        if not os.path.exists(self.panda3dDevDir):
            self.notify.error('Panda3D development SDK not found! Unable to build resources.')

        self.notify.info('Building the resources...')
        destDir = os.path.join(self.builtDir, 'resources')
        if not os.path.exists(destDir):
            os.makedirs(destDir)

        resourcesDir = os.path.join(self.baseDir, 'resources')
        for phase in os.listdir(resourcesDir):
            if not phase.startswith('phase_'):
                continue

            filename = phase + '.mf'
            filepath = os.path.join(destDir, filename)
            returnCode = subprocess.check_call([os.path.join(self.panda3dDevDir, 'bin', 'multify'), '-c', '-f', filepath, phase], cwd=resourcesDir)
            if returnCode == 0:
                self.notify.info('%s built successfully!' % phase)

        self.notify.info('All resources built successfully!')

    def run(self, command):
        self.builtDir = os.path.join(self.workingDir, 'built')
        if not os.path.exists(self.builtDir):
            os.makedirs(self.builtDir)

        if command == 'buildGame':
            self.copyBuildFiles()
            self.generateGameData(self.configFile)
            self.buildGame()
            self.copyToBuiltDir()
        elif command == 'buildResources':
            self.buildResources()
        else:
            self.notify.error('Unknown command: %s' % command)


class FunnyFarmCompilerWindows(FunnyFarmCompilerBase):
    notify = DirectNotifyGlobal.directNotify.newCategory('FunnyFarmCompilerWindows')

    def __init__(self, version, arch):
        FunnyFarmCompilerBase.__init__(self, version)
        self.arch = arch
        self.workingDir = os.path.join(self.workingDir, self.arch)
        self.panda3dProdDir = os.path.join(self.rootDir, 'funny-farm-panda3d', 'built_prod_%s' % self.arch)

    def removeOldBuildFiles(self):
        # on windows we want to preserve the build directory
        # as it contains cache which will speed up the build
        # process if we need to build the game again.
        if os.path.exists(self.workingDir):
            self.notify.info('Cleaning up old build files...')
            for item in os.listdir(self.workingDir):
                if item == 'built' or item == '%s.build' % os.path.splitext(os.path.basename(self.mainFile))[0]:
                    continue

                itemPath = os.path.join(self.workingDir, item)
                if os.path.isdir(itemPath):
                    shutil.rmtree(itemPath)
                else:
                    os.remove(itemPath)

    def copyToBuiltDir(self):
        self.notify.info('Copying to built directory...')
        distDir = os.path.join(self.workingDir, '%s.dist' % os.path.splitext(os.path.basename(self.mainFile))[0])
        if not os.path.exists(distDir):
            return

        gameFiles = [
            'cg.dll',
            'funnyfarm.exe',
            'libcrypto-1_1.dll',
            'libp3direct.dll',
            'libp3dtool.dll',
            'libp3dtoolconfig.dll',
            'libp3interrogatedb.dll',
            'libpanda.dll',
            'libpandaexpress.dll',
            'libpandaphysics.dll',
            'libssl-1_1.dll',
            'python37.dll',
            'select.pyd',
            '_cffi_backend.pyd',
            '_socket.pyd',
            '_ssl.pyd',
            'panda3d/core.pyd',
            'panda3d/direct.pyd',
            'panda3d/physics.pyd',
            'cryptography/hazmat/bindings/_constant_time.pyd',
            'cryptography/hazmat/bindings/_openssl.pyd',
            'cryptography/hazmat/bindings/_padding.pyd'
        ]

        for gameFile in gameFiles:
            basename = os.path.basename(gameFile)
            sourceDirName = os.path.dirname(gameFile)
            destDirName = ''
            if sourceDirName:
                destDirName = os.path.join(self.builtDir, sourceDirName)
                if not os.path.exists(destDirName):
                    os.makedirs(destDirName)

                shutil.copy(os.path.join(distDir, sourceDirName, basename), os.path.join(destDirName, basename))
            else:
                shutil.copy(os.path.join(distDir, sourceDirName, basename), os.path.join(self.builtDir, destDirName, basename))

        if not os.path.exists(self.panda3dProdDir):
            return

        pandaDlls = [
            'libpandagl.dll',
            'libp3windisplay.dll',
            'cgGL.dll',
            'libp3openal_audio.dll'
        ]

        for pandaDll in pandaDlls:
            shutil.copy(os.path.join(self.panda3dProdDir, 'bin', pandaDll), self.builtDir)

        self.notify.info('Successfully copied to built directory!')


class FunnyFarmCompilerDarwin(FunnyFarmCompilerBase):
    notify = DirectNotifyGlobal.directNotify.newCategory('FunnyFarmCompilerDarwin')

    def __init__(self, version):
        FunnyFarmCompilerBase.__init__(self, version)
        self.panda3dProdDir = os.path.join(self.rootDir, 'funny-farm-panda3d', 'built_prod_darwin')


parser = argparse.ArgumentParser(description='Build script for Toontown\'s Funny Farm')
parser.add_argument('--version', '-v', help='Game version', required=True)
parser.add_argument('--resources', '-r', help='Builds the game resources (phases).', action='store_true')
parser.add_argument('--game', '-g', help='Builds the game source code.', action='store_true')
parser.add_argument('--dist', '-d', help='Generate dist (patch manifest) files.', action='store_true')
if sys.platform == 'win32':
    parser.add_argument('--arch', '-a', help='Target architecture', choices=['win32', 'win64'], required=True)

args = parser.parse_args()

if sys.platform not in ('win32', 'darwin'):
    raise Exception('Platform not supported: %s' % sys.platform)

if (args.game or args.dist or args.resources):
    if sys.platform == 'win32':
        compiler = FunnyFarmCompilerWindows(args.version, args.arch)
    elif sys.platform == 'darwin':
        compiler = FunnyFarmCompilerDarwin(args.version)

if args.game:
    compiler.addSourceDir('libotp')
    compiler.addSourceDir('otp')
    compiler.addSourceDir('toontown')
    compiler.setMainFile(os.path.join(compiler.dataDir, 'funnyfarm.py'))
    compiler.setConfigFile(os.path.join('config', 'release.prc'))
    compiler.run('buildGame')

if args.resources:
    compiler.run('buildResources')
