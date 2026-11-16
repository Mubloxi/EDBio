from edbio.audio import DEFAULT_SOUND, available_sounds, sound_file_path


def test_sound_catalog_keeps_folders_as_categories():
    sounds = available_sounds()
    categories = {sound["category"] for sound in sounds}

    assert {"Normal", "French", "Trump", "Obama"} <= categories
    assert any(sound["path"] == DEFAULT_SOUND for sound in sounds)
    assert sound_file_path(DEFAULT_SOUND)


def test_sound_paths_cannot_escape_the_sound_folder():
    assert sound_file_path("../outside.mp3") is None
