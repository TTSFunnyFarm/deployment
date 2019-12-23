assert not __debug__  # Run with -OO

import codecs
from cryptography.fernet import Fernet
import os

FUNNY_FARM_SRC_DIR = 'Toontowns-Funny-Farm'
BUILT_DIR = 'built'

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

def generateConfigData():
    print('Generating config data...')
    config = getFileContents(FUNNY_FARM_SRC_DIR + '/config/release.prc', True)
    configData = 'CONFIG = %r\n' % config
    with open(BUILT_DIR + '/configdata.py', 'w') as f:
        f.write(configData)
        f.close()


generateConfigData()
