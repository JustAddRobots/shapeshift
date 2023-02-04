#!/usr/bin/env python3

"""
This module defines important custom errors that have a frequent use case.
"""

# Exception.args must be a tuple


class ShellCommandExecutionError(Exception):

    def __init__(self, d_args):
        self.msg = "Command failed with non-zero return code."
        self.args = list(d_args.items())

    def __str__(self):
        return self.msg


class NullValueError(Exception):

    def __init__(self):
        self.msg = "Variable has null value."

    def __str__(self):
        return self.msg
