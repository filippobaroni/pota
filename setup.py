#!/usr/bin/env python3

from setuptools import setup, find_packages

setup(name = 'pota',
      version = '0.1.1',
      description = 'Pota interpreter.',
      author = 'Delfad0r',
      author_email = 'filippo.gianni.baroni@gmail.com',
      license = 'LGPL3',
      url = 'https://github.com/Delfad0r/pota',
      packages = find_packages(),
      entry_points = {
          'console_scripts' : [
              'pota=pota.pota:main'
          ]
      })
