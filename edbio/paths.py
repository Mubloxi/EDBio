"""Resolve resource files both during development and after PyInstaller bundling."""

import os
import sys


def resource_path(relative):
    """Absolute path to a resource bundled with the application.

    During development this points at the file next to the package.
    When frozen by PyInstaller, it points into the extracted bundle (_MEIPASS).
    """
    if getattr(sys, "frozen", False):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, relative)


def user_data_dir():
    """Persistent user data directory (%APPDATA%\\EDBio), outside the install dir."""
    appdata = os.environ.get("APPDATA", os.path.expanduser("~"))
    path = os.path.join(appdata, "EDBio")
    os.makedirs(path, exist_ok=True)
    return path
