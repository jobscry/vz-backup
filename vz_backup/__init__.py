# -*- mode: python; coding: utf-8; -*-
VERSION = (0, 1, 0)
__version__ = '.'.join(map(str, VERSION))
__author__ = 'Joe Vasquez'
__email__ = 'joe.vasquez@gmail.com'
__license__ = 'MIT'

import hashlib

def generate_file_hash(path):
    file_hash = hashlib.sha1()
    with open(path, 'rb') as f:
        data = f.read(4096)
        while data != '':
            file_hash.update(data)
            data = f.read(4096)
    return file_hash.hexdigest()
