#!/usr/bin/env python

from setuptools import setup, Extension

setup(name='wss',
      version='1.1',
      description='Python Secure Websockets server/client that uses asyncio and authobahn',
      author='Kevron Rees',
      author_email='tripzero.kev@gmail.com',
      url='https://github.com/tripzero/python-wss',
      packages=["wss"],
      install_requires=["trollius", "autobahn"]
      )

