#!/usr/bin/env python3

"""
This module contains functions for testing variables at run-time.
"""

import collections
import logging
import pprint

from . import error


logger = logging.getLogger(__name__)


def get_debug(var, **kwargs):
    """Get pprint of variable.

    Args:
        var (any):

    Kwargs:
        sort_dicts (bool): Sort dictionaries by key.

    Returns:
        var_pprint (PrettyPrinter): pprint of var.
    """
    my_sort_dicts = kwargs.setdefault("sort_dicts", True)
    if isinstance(var, collections.Callable):
        attrs = var.__module__ + "." + var.__name__
    else:
        try:
            attrs = vars(var)
        except TypeError:
            attrs = var
    var_pprint = pprint.pformat(
        attrs,
        width=160,
        compact=True,
        sort_dicts=my_sort_dicts
    )
    return var_pprint


def check_null(var):
    """Raise error if variable is null.

    Args:
        var (any): Variable to check.

    Returns:
        None

    Raises:
        error.NullValueError: Variable has null value.
    """
    if not var:
        try:
            raise error.NullValueError()
        except error.NullValueError:
            logger.error("Null Value Error")
            raise
    return None
