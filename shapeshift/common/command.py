#!/usr/bin/env python3

"""
This module contains functions used to execute shell commands.
"""

import glob
import logging
import os
import shlex
import subprocess
import time

from . import error
from . import testvar
from .constants import _const as CONSTANTS

logger = logging.getLogger(__name__)


def check_returncode(cmd, ret_code):
    """Check the returncode of a command. Raise if problematic.
    Some commands are broken and some commands must be ignored.

    Args:
        cmd (str): Command to check.
        ret_code (str): Return code.

    Returns:
        None

    Raises:
        error.ShellCommandExecutionError: Error executing command.
    """
    ignore_returncode = False
    if isinstance(cmd, list):
        cmd = " ".join(cmd)
    if ret_code != 0:
        for k, v in CONSTANTS().IGNORE_RETURNCODE.items():
            if cmd.startswith(k) and ret_code == v:
                ignore_returncode = True
                break
        if not ignore_returncode:
            try:
                raise error.ShellCommandExecutionError({
                    'ret_code': ret_code,
                    'cmd': cmd,
                })
            except error.ShellCommandExecutionError as e:
                logger.info(testvar.get_debug(e.args))
                logger.error("Shell Command Execution Error")
                raise
    return None


def call_shell_cmd(cmd, stdout=None, stderr=subprocess.STDOUT, **kwargs):
    """Run shell command, disregard the output.

    Args:
        cmd (str): Command to run.

    Kwargs:
        cwd (str): Current working dir from which to run cmd.
        shell (bool): Run command in shell mode.
        add_env (mapping): Environment variable mapping.

    Returns:
        None

    Raises:
        OSError: Error starting command.
    """
    my_cwd = kwargs.setdefault("cwd", None)
    my_shell = kwargs.setdefault("shell", False)
    my_env = kwargs.setdefault("add_env", os.environ.copy())
    if not(stdout):
        FNULL = open(os.devnull, 'w')
        stdout = FNULL

    if ("|" in cmd) or ('*' in cmd) or ('?' in cmd):
        my_shell = True
    else:
        cmd = shlex.split(cmd)

    try:
        p = subprocess.Popen(
            cmd,
            shell = my_shell,
            stdout = stdout,
            stderr = stderr,
            cwd = my_cwd,
            env = my_env,
            close_fds = True,
        )
    except OSError:
        logger.error("Shell Command Start Error")
        logger.debug(testvar.get_debug((cmd, my_cwd, my_shell)))
        raise
    else:
        p.communicate()
        ret_code = p.returncode
        check_returncode(cmd, ret_code)
    time.sleep(1)
    return None


def cmd_cleanup(cmd):
    """Create a command list from shell command.

    Process a shell command into a list to be processed by
    subprocess.Popen. Quotes are handled. Wildcards are expanded.
    Regex is passed through.

    Args:
        cmd (str): Command to be parsed.

    Returns:
        cmd_list (list): Parsed commands.
    """
    cmd_list = []
    cmd_split = shlex.split(cmd)
    regex_cmds = [
        "sed",
        "grep",
        "egrep",
    ]
    for arg in cmd_split:
        if (
            (("*" in arg) or ("?" in arg))
            and (cmd_split[0] not in regex_cmds)
        ):
            arg = glob.glob(arg)
            cmd_list.extend(arg)
        else:
            cmd_list.append(arg)
    return cmd_list


def get_shell_cmd(cmd, **kwargs):
    """Get shell command output.

    Args:
        cmd (str): Command to run.

    Kwargs:
        cwd (str): Current working dir from which to run cmd.
        encoding (str): Text encoding.

    Returns:
        dict(
            ret_code (str): Return code.
            stdout (str): STDOUT.
            stderr (str): STDERR.
        )
    Raises:
        OSError: Error starting shell command.
        KeyboardInterrupt: CTRL-C caught while running command.
    """
    my_cwd = kwargs.setdefault("cwd", None)
    my_encoding = kwargs.setdefault("encoding", 'utf-8')
    my_stdin = None
    cmd_list = []

    # Create command list from pipes for chaining in subprocess.Popen
    if "|" in cmd:
        cmd_list = cmd.split("|")
    else:
        cmd_list.append(cmd)

    for i, cmd in enumerate(cmd_list):
        cmd = cmd_cleanup(cmd)
        try:
            p = subprocess.Popen(
                cmd,
                shell = False,
                stdin = subprocess.PIPE,
                stdout = subprocess.PIPE,
                stderr = subprocess.PIPE,
                cwd = my_cwd,
                encoding = my_encoding,
            )
        except OSError:
            logger.error("Shell Command Start Error")
            logger.debug("cmd: {0}".format(cmd))
            raise
        else:
            try:
                r = p.communicate(my_stdin)
            except KeyboardInterrupt:
                logger.error("Keyboard Interrupt, sending SIGTERM")
                logger.debug(testvar.get_debug(cmd))
                p.terminate()
                raise
            else:
                stderr = r[1]
                ret_code = p.returncode
                check_returncode(cmd, ret_code)
                if i == (len(cmd_list) - 1):  # Last command
                    stdout = r[0]
                else:  # Otherwise pipe to next command
                    my_stdin = r[0]

    return {
        'ret_code': ret_code,
        'stdout': stdout,
        'stderr': stderr
    }
