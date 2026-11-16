import os

import pytest

from audio import (
    DEFAULT_SOUND, available_sounds, import_custom_sound, sound_file_path,
)


def test_sound_catalog_keeps_folders_as_categories():
    sounds = available_sounds()
    categories = {sound["category"] for sound in sounds}

    assert {"Normal", "French", "Trump", "Obama"} <= categories
    assert any(sound["path"] == DEFAULT_SOUND for sound in sounds)
    assert sound_file_path(DEFAULT_SOUND)


def test_sound_paths_cannot_escape_the_sound_folder():
    assert sound_file_path("../outside.mp3") is None


def test_custom_sounds_are_copied_and_listed(monkeypatch, tmp_path):
    source = tmp_path / "my-alert.wav"
    source.write_bytes(b"custom sound")
    destination = tmp_path / "custom-sounds"
    monkeypatch.setattr("audio.CUSTOM_SOUND_DIRECTORY", str(destination))

    relative_path = import_custom_sound(str(source))

    assert relative_path == "custom/my-alert.wav"
    assert (destination / "my-alert.wav").read_bytes() == b"custom sound"
    assert sound_file_path(relative_path) == os.path.abspath(destination / "my-alert.wav")
    assert any(
        sound["path"] == relative_path and sound["category"] == "Custom sounds"
        for sound in available_sounds()
    )


def test_custom_sound_rejects_unsupported_extensions(tmp_path):
    source = tmp_path / "alert.txt"
    source.write_text("not audio")

    with pytest.raises(ValueError, match="MP3, WAV, or OGG"):
        import_custom_sound(str(source))
