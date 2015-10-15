import os
import sys
from . import zenpacklib

libDir = os.path.join(os.path.dirname(__file__), 'lib')
if os.path.isdir(libDir):
    sys.path.append(libDir)
    for file in os.listdir(libDir):
        if file.endswith('.egg'):
            sys.path.append(os.path.join(libDir, file))

zenpacklib.load_yaml()

