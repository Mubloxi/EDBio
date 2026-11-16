"""Build EDBio.exe with PyInstaller.

Run from the project root:

    python build_exe.py

Produces a standalone EDBio.exe in dist/ (one windowed executable, no console).
"""

import os
import PyInstaller.__main__ as pyi

ROOT = os.path.dirname(os.path.abspath(__file__))

# Files to bundle alongside the executable.
# format: source_path;dest_folder  (Windows uses ';' as the separator)
add_data = [
    (os.path.join(ROOT, "edbio", "data"), "edbio/data"),
    (os.path.join(ROOT, "edbio", "resources"), "edbio/resources"),
    (os.path.join(ROOT, "sfx"), "sfx"),
]

pyi_args = [
    "edbio/main.py",
    "--name", "EDBio",
    "--onefile",
    "--windowed",           # no console window
    "--icon", os.path.join(ROOT, "edbio", "resources", "icon.ico"),
    "--clean",
    "--log-level", "INFO",
]
for src, dst in add_data:
    pyi_args += ["--add-data", f"{src}{os.pathsep}{dst}"]

pyi.run(pyi_args)

if __name__ == "__main__":
    print("Building EDBio.exe...")
