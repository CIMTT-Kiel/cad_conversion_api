"""
This module defines several constants used throughout the CAD API client.

The module provides access to path constants that make navigation through
the project structure easier and more maintainable.

Examples
--------
>>> from client import constants
>>> # get Path object for the project root directory
>>> constants.PATHS.ROOT
>>> # get Path object for the config directory
>>> constants.PATHS.CONFIG
"""
from pathlib import Path
from collections import namedtuple


# Paths
# From client/src/client/constants.py: parents[3] gets to project root
_ROOT = Path(__file__).parents[3]
_path_dict = {
    "ROOT": _ROOT,
    "CONFIG": _ROOT / "config",
}

# Create NamedTuple for attribute access
Paths = namedtuple("Paths", _path_dict.keys())
PATHS = Paths(**_path_dict)
