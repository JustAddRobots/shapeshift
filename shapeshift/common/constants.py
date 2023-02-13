#!/usr/bin/env python3

"""
This module defines package constants.
"""


def constant(f):
    def fset(self, value):
        raise TypeError

    def fget(self):
        return f()
    return property(fget, fset)


class _const(object):

    @constant
    def CUSTOM_COLLECTIONS_PREFIX():
        return "MY_"

    @constant
    def SM_PREFIX():
        return "SM_"

    @constant
    def TEXTURE_RES():
        return 2048

    @constant
    def IGNORE_RETURNCODE():
        return {
            "grep": 1,
        }
