assert not __debug__  # Run with -OO

import argparse
import bz2
from collections import OrderedDict
import hashlib
import json
import os
import shutil
import subprocess
import sys

from cryptography.fernet import Fernet
from direct.directnotify import DirectNotifyGlobal


class FunnyFarmCompilerBase:
    notify = DirectNotifyGlobal.directNotify.newCategory('FunnyFarmCompilerBase')

    def __init__(self, version, launcherVersion):
        self.version = version
        self.launcherVersion = launcherVersion
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

        self.notify.info('Build files copied successfully.')

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

        self.notify.info('Config data generated successfully.')

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

    def getDistributables(self):
        # This is entirely platform dependent and must be overriden by subclass.
        raise NotImplementedError('getDistributables')

    def getFileMD5Hash(self, filepath):
        md5 = hashlib.md5()
        readBlock = lambda: f.read(128 * md5.block_size)
        with open(filepath, 'rb') as f:
            for chunk in iter(readBlock, b''):
                md5.update(chunk)

        return md5.hexdigest()

    def writeManifest(self):
        self.notify.info('Writing patch manifest...')
        distDir = os.path.join(self.builtDir, 'dist')
        os.chdir(self.builtDir)
        manifest = OrderedDict()
        manifest['files'] = OrderedDict()
        self.notify.info('Writing files to patch manifest...')
        for filepath in self.getDistributables():
            self.notify.info('Adding %s...' % filepath)
            manifest['files'][filepath] = OrderedDict()
            manifest['files'][filepath]['path'] = os.path.dirname(filepath)
            manifest['files'][filepath]['hash'] = self.getFileMD5Hash(filepath)

        self.notify.info('Files written to patch manifest successfully.')

        gameVersion = self.version.strip('v')
        self.notify.info('Writing game-version...')
        self.notify.info('game-version: %s' % gameVersion)
        manifest['game-version'] = gameVersion

        launcherVersion = self.launcherVersion.strip('v')
        self.notify.info('Writing launcher-version...')
        self.notify.info('launcher-version: %s' % launcherVersion)
        manifest['launcher-version'] = launcherVersion

        self.notify.info('Writing the patch manifest data to manifest.json...')
        with open(os.path.join(distDir, 'manifest.json'), 'w') as f:
            f.write(json.dumps(manifest, indent=4))
            f.close()

        os.chdir(self.rootDir)
        self.notify.info('Successfully wrote patch manifest.')

    def compressFile(self, filepath):
        distDir = os.path.join(self.builtDir, 'dist')
        with open(filepath, 'rb') as f:
            data = f.read()

        filename = os.path.basename(filepath)
        directory = os.path.dirname(filepath)
        if not os.path.exists(os.path.join(distDir, directory)):
            os.makedirs(os.path.join(distDir, directory))

        bz2Filename = filename + '.bz2'
        bz2Filepath = os.path.join(distDir, directory, bz2Filename)
        f = bz2.BZ2File(bz2Filepath, 'w')
        f.write(data)
        f.close()

    def compressFiles(self):
        self.notify.info('Compressing distributables...')
        os.chdir(self.builtDir)
        for filepath in self.getDistributables():
            self.notify.info('Compressing: %s' % filepath)
            self.compressFile(filepath)

        os.chdir(self.rootDir)
        self.notify.info('Successfully compressed distributables.')

    def buildDist(self):
        self.notify.info('Building distributables...')
        distDir = os.path.join(self.builtDir, 'dist')
        if not os.path.exists(distDir):
            os.makedirs(distDir)

        self.writeManifest()
        self.compressFiles()

        self.notify.info('Done building distributables.')

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
        elif command == 'buildDist':
            self.buildDist()
        else:
            self.notify.error('Unknown command: %s' % command)


class FunnyFarmCompilerWindows(FunnyFarmCompilerBase):
    notify = DirectNotifyGlobal.directNotify.newCategory('FunnyFarmCompilerWindows')

    def __init__(self, version, launcherVersion, arch):
        FunnyFarmCompilerBase.__init__(self, version, launcherVersion)
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

    def getDistributables(self):
        distributables = [
            'cg.dll',
            'cgGL.dll',
            'funnyfarm.exe',
            'libcrypto-1_1.dll',
            'libp3direct.dll',
            'libp3dtool.dll',
            'libp3dtoolconfig.dll',
            'libp3interrogatedb.dll',
            'libp3openal_audio.dll',
            'libp3windisplay.dll',
            'libpanda.dll',
            'libpandaexpress.dll',
            'libpandagl.dll',
            'libpandaphysics.dll',
            'libssl-1_1.dll',
            'python37.dll',
            'select.pyd',
            '_cffi_backend.pyd',
            '_socket.pyd',
            '_ssl.pyd',
            'resources/phase_3.5.mf',
            'resources/phase_3.mf',
            'resources/phase_4.mf',
            'resources/phase_5.5.mf',
            'resources/phase_5.mf',
            'resources/phase_6.mf',
            'resources/phase_7.mf',
            'resources/phase_8.mf',
            'resources/phase_9.mf',
            'resources/phase_10.mf',
            'resources/phase_11.mf',
            'resources/phase_12.mf',
            'resources/phase_13.mf',
            'resources/phase_14.mf',
            'panda3d/core.pyd',
            'panda3d/direct.pyd',
            'panda3d/physics.pyd',
            'cryptography/hazmat/bindings/_constant_time.pyd',
            'cryptography/hazmat/bindings/_openssl.pyd',
            'cryptography/hazmat/bindings/_padding.pyd'
        ]
        return distributables


class FunnyFarmCompilerDarwin(FunnyFarmCompilerBase):
    notify = DirectNotifyGlobal.directNotify.newCategory('FunnyFarmCompilerDarwin')

    def __init__(self, version, launcherVersion):
        FunnyFarmCompilerBase.__init__(self, version, launcherVersion)
        self.panda3dProdDir = os.path.join(self.rootDir, 'funny-farm-panda3d', 'built_prod_darwin')


parser = argparse.ArgumentParser(description='Build script for Toontown\'s Funny Farm')
parser.add_argument('--version', '-v', help='Game version', required=True)
parser.add_argument('--launcher', '-l', help='Launcher version')
parser.add_argument('--resources', '-r', help='Builds the game resources (phases).', action='store_true')
parser.add_argument('--game', '-g', help='Builds the game source code.', action='store_true')
parser.add_argument('--dist', '-d', help='Generate distributable (patch manifest) files.', action='store_true')
if sys.platform == 'win32':
    parser.add_argument('--arch', '-a', help='Target architecture', choices=['win32', 'win64'], required=True)

args = parser.parse_args()

if sys.platform not in ('win32', 'darwin'):
    raise Exception('Platform not supported: %s' % sys.platform)

if args.dist and not args.launcher:
    raise Exception('Launcher version must be set to build distributables!')

if (args.game or args.dist or args.resources):
    if sys.platform == 'win32':
        compiler = FunnyFarmCompilerWindows(args.version, args.launcher, args.arch)
    elif sys.platform == 'darwin':
        compiler = FunnyFarmCompilerDarwin(args.version, args.launcher)

if args.game:
    compiler.addSourceDir('libotp')
    compiler.addSourceDir('otp')
    compiler.addSourceDir('toontown')
    compiler.setMainFile(os.path.join(compiler.dataDir, 'funnyfarm.py'))
    compiler.setConfigFile(os.path.join('config', 'release.prc'))
    compiler.run('buildGame')

if args.resources:
    compiler.run('buildResources')

if args.dist:
    compiler.run('buildDist')
