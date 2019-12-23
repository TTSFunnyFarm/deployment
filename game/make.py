assert not __debug__  # Run with -OO

import codecs
from cryptography.fernet import Fernet
import os
import shutil

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
    if not os.path.exists(FUNNY_FARM_SRC_DIR):
        return

    print('Generating config data...')
    config = getFileContents(FUNNY_FARM_SRC_DIR + '/config/release.prc', True)
    gameData = 'CONFIG = %r\n' % config
    with open(BUILT_DIR + '/gamedata.py', 'w') as f:
        f.write(gameData)
        f.close()

def copyFiles():
    print('Copying files...')
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


generateGameData()
copyFiles()
