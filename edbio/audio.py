"""Sound effect catalog for biological-signal notifications."""

import os

from .paths import resource_path


DEFAULT_SOUND = "random ass/notification.mp3"
SOUND_DIRECTORY = resource_path("sfx")

_CATEGORY_LABELS = {
    "random ass": "Normal",
    "french": "French",
    "trump": "Trump",
    "obama": "Obama",
    "app notifications": "App notifications",
}
_CATEGORY_ORDER = ("random ass", "french", "trump", "obama", "app notifications")


def available_sounds():
    """Return sound entries grouped by their containing category directory."""
    if not os.path.isdir(SOUND_DIRECTORY):
        return []

    categories = [
        name for name in os.listdir(SOUND_DIRECTORY)
        if os.path.isdir(os.path.join(SOUND_DIRECTORY, name))
    ]
    categories.sort(key=lambda name: (
        _CATEGORY_ORDER.index(name.casefold())
        if name.casefold() in _CATEGORY_ORDER else len(_CATEGORY_ORDER),
        name.casefold(),
    ))

    sounds = []
    for category in categories:
        directory = os.path.join(SOUND_DIRECTORY, category)
        for filename in sorted(os.listdir(directory), key=str.casefold):
            if filename.casefold().endswith(".mp3"):
                sounds.append({
                    "category": _CATEGORY_LABELS.get(category.casefold(), category.title()),
                    "name": os.path.splitext(filename)[0],
                    "path": os.path.join(category, filename).replace(os.sep, "/"),
                })
    return sounds


def sound_file_path(relative_path):
    """Resolve a catalog-relative sound path within the bundled sound folder."""
    if not relative_path:
        return None
    path = os.path.abspath(os.path.join(SOUND_DIRECTORY, relative_path.replace("/", os.sep)))
    if os.path.commonpath((os.path.abspath(SOUND_DIRECTORY), path)) != os.path.abspath(SOUND_DIRECTORY):
        return None
    return path
