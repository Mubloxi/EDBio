# build in rust and package as a standalone executable with python


import os
import shutil
import subprocess
import sys

import PyInstaller.__main__ as pyi


ROOT = os.path.dirname(os.path.abspath(__file__))


def build_native_reader():
    if sys.platform != "win32":
        raise RuntimeError("The standalone EDBio build currently targets Windows.")
    environment = os.environ.copy()
    environment["PYO3_PYTHON"] = sys.executable
    manifest = os.path.join(ROOT, "journal_native", "Cargo.toml")
    cargo_args = [
        "cargo",
        "build",
        "--manifest-path",
        manifest,
        "--release",
    ]

    program_files = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
    vswhere = os.path.join(
        program_files, "Microsoft Visual Studio", "Installer", "vswhere.exe"
    )
    if os.path.isfile(vswhere):
        result = subprocess.run(
            [
                vswhere,
                "-latest",
                "-products", "*",
                "-requires", "Microsoft.VisualStudio.Component.VC.Tools.x86.x64",
                "-property", "installationPath",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        installation = result.stdout.strip()
        vcvars = os.path.join(
            installation, "VC", "Auxiliary", "Build", "vcvars64.bat"
        )
    else:
        vcvars = ""

    if vcvars and os.path.isfile(vcvars):
        command = (
            f'call "{vcvars}" >nul && cargo build '
            f'--manifest-path "{manifest}" --release'
        )
        subprocess.run(command, cwd=ROOT, check=True, env=environment, shell=True)
    else:
        subprocess.run(cargo_args, cwd=ROOT, check=True, env=environment)

    source = os.path.join(
        ROOT, "journal_native", "target", "release", "journal_native.dll"
    )
    destination = os.path.join(ROOT, "journal_native.pyd")
    shutil.copy2(source, destination)
    return destination


def build_web_panel():
    subprocess.run(
        ["cmd.exe", "/d", "/s", "/c", "npm.cmd ci"],
        cwd=ROOT,
        check=True,
    )
    subprocess.run(
        ["cmd.exe", "/d", "/s", "/c", "npm.cmd run build"],
        cwd=ROOT,
        check=True,
    )


def build_executable(components_only=False):
    native_extension = build_native_reader()
    build_web_panel()
    if components_only:
        return

    add_data = [
        (os.path.join(ROOT, "data"), "data"),
        (os.path.join(ROOT, "resources"), "resources"),
        (os.path.join(ROOT, "sfx"), "sfx"),
        (os.path.join(ROOT, "web"), "web"),
    ]
    args = [
        "main.py",
        "--name", "EDBio",
        "--onefile",
        "--windowed",
        "--icon", os.path.join(ROOT, "resources", "icon.ico"),
        "--clean",
        "--log-level", "INFO",
        "--hidden-import", "journal_native",
        "--hidden-import", "PySide6.QtWebChannel",
        "--hidden-import", "PySide6.QtWebEngineWidgets",
        "--add-binary", f"{native_extension}{os.pathsep}.",
    ]
    for source, destination in add_data:
        args += ["--add-data", f"{source}{os.pathsep}{destination}"]
    pyi.run(args)


if __name__ == "__main__":
    build_executable(components_only="--components-only" in sys.argv[1:])
