#!/usr/bin/env python3

from setuptools import setup, find_packages

version="1.1"

classifiers = [
    'Development Status :: 4 - Beta',
    'Intended Audience :: Developers',
    'Topic :: Software Development :: Build Tools',
    'License :: OSI Approved :: GNU Lesser General Public License v2 or later (LGPLv2+)',
    'Programming Language :: Python :: 3',
    'Programming Language :: Python :: 3.2',
    'Programming Language :: Python :: 3.3',
    'Programming Language :: Python :: 3.4',
    'Programming Language :: Python :: 3.5',
    'Programming Language :: Python :: 3.6',
]

setup(name='wss',
      version=version,
      description='Python Secure Websockets server/client that uses asyncio and authobahn',
      author='Kevron Rees',
      author_email='tripzero.kev@gmail.com',
      license='LGPLv2+',
      classifiers=classifiers,
      url='https://github.com/tripzero/python-wss',
      packages=["wss"],
      install_requires=["autobahn"],
      include_package_data = True)
