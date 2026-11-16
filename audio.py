"""Sound effect catalog for biological-signal notifications."""

import os
import shutil
import uuid

from paths import resource_path, user_data_dir


DEFAULT_SOUND = "random ass/notification.mp3"
SOUND_DIRECTORY = resource_path("sfx")
CUSTOM_SOUND_DIRECTORY = os.path.join(user_data_dir(), "Sounds")

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
    if os.path.isdir(CUSTOM_SOUND_DIRECTORY):
        for filename in sorted(os.listdir(CUSTOM_SOUND_DIRECTORY), key=str.casefold):
            if filename.casefold().endswith((".mp3", ".wav", ".ogg")):
                sounds.append({
                    "category": "Custom sounds",
                    "name": os.path.splitext(filename)[0],
                    "path": f"custom/{filename}",
                })
    return sounds


def sound_file_path(relative_path):
    """Resolve a catalog-relative sound path within the bundled sound folder."""
    if not relative_path:
        return None
    relative_path = relative_path.replace("/", os.sep)
    if relative_path.startswith(f"custom{os.sep}"):
        root = os.path.abspath(CUSTOM_SOUND_DIRECTORY)
        relative_path = relative_path[len(f"custom{os.sep}"):]
    else:
        root = os.path.abspath(SOUND_DIRECTORY)
    try:
        path = os.path.abspath(os.path.join(root, relative_path))
        if os.path.commonpath((root, path)) != root:
            return None
    except ValueError:
        return None
    return path


def import_custom_sound(source_path):
    """Copy a user-selected audio file into EDBio's custom sound folder."""
    extension = os.path.splitext(source_path)[1].casefold()
    if extension not in {".mp3", ".wav", ".ogg"}:
        raise ValueError("Choose an MP3, WAV, or OGG sound file.")
    if not os.path.isfile(source_path):
        raise FileNotFoundError(source_path)

    os.makedirs(CUSTOM_SOUND_DIRECTORY, exist_ok=True)
    filename = os.path.basename(source_path)
    destination = os.path.join(CUSTOM_SOUND_DIRECTORY, filename)
    if os.path.abspath(source_path) == os.path.abspath(destination):
        return f"custom/{filename}"
    if os.path.exists(destination):
        stem, extension = os.path.splitext(filename)
        destination = os.path.join(
            CUSTOM_SOUND_DIRECTORY, f"{stem}-{uuid.uuid4().hex[:8]}{extension}"
        )
        filename = os.path.basename(destination)

    shutil.copy2(source_path, destination)
    return f"custom/{filename}"
