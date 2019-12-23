assert not __debug__  # Run with -OO

import os

FUNNY_FARM_SRC_DIR = 'Toontowns-Funny-Farm/'
PANDA3D_DIR = 'C:\\Panda3D-1.10.4.1-x64'

if not os.path.exists(FUNNY_FARM_SRC_DIR):
    raise FileNotFoundError('Unable to locate the Toontown\'s Funny Farm game source code! Make sure to clone the Toontown\'s Funny Farm game source code repository into this directory.')

if not os.path.exists(PANDA3D_DIR):
    raise FileNotFoundError('Unable to locate the Panda3D SDK! Make sure to install the Panda3D SDK linked in the game source code repository\'s README.')
