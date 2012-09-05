#!/usr/bin/env python2
# -*- coding: utf-8 -*-

from distutils.core import setup, Extension
import subprocess

flags = subprocess.check_output(["pkg-config", "--libs", "gnokii"])

module1 = Extension('waitsms', sources=['waitsms.c', 'waitsmsmod.c'],
    extra_compile_args=["-W", "-Wall"],
    extra_link_args=flags.strip().split(" "))

setup (name = 'WaitSMS',
       version = '1.0',
       description = 'SMS getter',
       ext_modules = [module1])
