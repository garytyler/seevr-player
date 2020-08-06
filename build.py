import json
import os
import sys
import tempfile
from glob import glob
from subprocess import check_call
import shutil
import typer
import PyInstaller.__main__
import subprocess

def is_mac():
    return sys.platform == "darwin"

def is_linux():
    return sys.platform == "linux"

def is_windows():
    return sys.platform == "win32"

def verify_supported_platform():
    if not any((is_mac(), is_linux(), is_windows())):
        github_url = "https://github.com/garytyler/seevr-player/issues"
        raise RuntimeError(f"Platform unsupported. Request support at {github_url}")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class BuildSettings(dict):
    def __init__(self):
        self.file_path = os.path.join(BASE_DIR, "build.json")
        with open(self.file_path) as f:
            data = json.loads(f.read())
        self.update(data.get("base", {}))
        if is_mac():
            self.update(data.get("mac", {}))
        if is_linux():
            self.update(data.get("linux", {}))
        if is_windows():
            self.update(data.get("windows", {}))

    def __getitem__(self, key: str) -> str:
        if key not in self:
            raise ValueError(f"'{key}' is not a valid dependency environment variable")
        else:
            return super().__getitem__(key)

    def __setitem__(self, key: str, value: str) -> None:
        raise RuntimeError(f"Build configuration is read-only:'{self.file_path}'")


BUILD_SETTINGS = BuildSettings()
APP_MODULE = os.path.join(BASE_DIR, "app")
FREEZE_DIR = os.path.join(BASE_DIR, "dist", BUILD_SETTINGS["app_name"])


class DependencyEnvironment(dict):
    """Set/get dependency environment variables with helpful logs and exceptions."""

    _dependency_keys = [
        "PYTHON_VLC_LIB_PATH",
        "PYTHON_VLC_MODULE_PATH",
        "FFPROBE_BINARY_PATH",
    ]

    def __init__(self):
        super().__init__({})
        for key in self._dependency_keys:
            value = os.environ.get(key)
            if not value:
                super().__setitem__(key, None)
            elif not os.path.exists(value):
                raise FileNotFoundError(f"'{key}' value is non-existent path: {value}")
            else:
                super().__setitem__(key, value)
                print(f"Dependency source (user) - key={key}, value={value}")

    def __setitem__(self, key: str, value: str) -> None:
        if key not in self._dependency_keys:
            raise ValueError(f"'{key}' is not a valid dependency environment variable")
        elif not os.path.exists(value):
            raise FileNotFoundError(f"'{key}' value is non-existent path: {value}")
        else:
            print(f"Dependency source (default) - key={key}, value={value}")
            super().__setitem__(key, value)

    def __getitem__(self, key: str) -> str:
        if key not in self._dependency_keys:
            raise ValueError(f"'{key}' is not a valid dependency environment variable")
        else:
            return super().__getitem__(key)


def create_build_env(self):
    freeze_proc_dir = tempfile.mkdtemp()

    venv_path = os.path.join(freeze_proc_dir, "release_venv")
    check_call([sys.executable, "-m", "venv", venv_path])

    req_txt = os.path.join(freeze_proc_dir, "requirements.txt")
    check_call(["poetry", "update"], shell=True)
    check_call(
        [
            "poetry",
            "export",
            "--dev",
            "--without-hashes",
            "-f",
            "requirements.txt",
            ">",
            req_txt,
        ],
        shell=True,
    )

    if is_windows():
        release_python = os.path.join(venv_path, "Scripts", "python.exe")
    else:
        release_python = os.path.join(venv_path, "bin", "python")

    check_call([release_python, "-m", "pip", "install", "-r", req_txt])
    check_call([release_python, "-m", "pip", "install", "-r", req_txt])
    return venv_path


cli = typer.Typer()


@cli.command()
def run():
    if is_mac():
        for i in ['PYTHON_VLC_LIB_PATH', 'PYTHON_VLC_MODULE_PATH']:
            try:
                del os.environ[i]
            except KeyError:
                pass

    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    extra_args = sys.argv[2:]
    for arg in extra_args:
        sys.argv.remove(arg)
    os.environ["_BUILD_SCRIPT_RUN_ARGS"] = ",".join(extra_args)

    subprocess.call([sys.executable, APP_MODULE])


@cli.command()
def freeze():
    shutil.rmtree(os.path.join(BASE_DIR, "dist"), ignore_errors=True)
    shutil.rmtree(os.path.join(BASE_DIR, "build"), ignore_errors=True)

    if is_windows():
        dep_environ = DependencyEnvironment()

    delimiter = ";" if is_windows() else ":"
    command = [
        "--log-level=INFO",
        "--noconfirm",
        "--clean",
        "--onedir",
        "--windowed",
        "--hidden-import=PyQt5.QtNetwork",
        "--hidden-import=PyQt5.QtCore",
        f"--name={BUILD_SETTINGS['app_name']}",
        f"--icon={os.path.join(BASE_DIR, 'icons', 'Icon.ico')}",
        f"--add-data={os.path.join(BASE_DIR, 'build.json')}{delimiter}.",
        f"--add-data={os.path.join(BASE_DIR, 'media')}{delimiter}media",
        f"--add-data={os.path.join(BASE_DIR, 'style')}{delimiter}style",
        f"--add-binary=/Users/g/proj/seevr-player/ffmpeg/ffprobe{delimiter}ffmpeg",
    ]

    if is_windows():
        command += [f"--additional-hooks-dir={os.path.join(BASE_DIR, 'hooks')}"]
        # add vlc binary paths args to satisfy warnings during bundling with hooks
        command += [f"--paths={p}" for p in dep_environ.values() if p and os.path.exists(p) and os.path.isdir(p)]
        command += [
            f"--paths={os.path.dirname(p)}"
            for p in dep_environ.values()
            if p and os.path.isfile(p)
        ]

    # call target script
    command.append(os.path.join(BASE_DIR, "app", "__main__.py"))
    PyInstaller.__main__.run(command)

@cli.command()
def installer():
    if is_mac():
        mounted_dmg_paths = glob(f"/Volumes/{BUILD_SETTINGS['app_name']}*")
        if mounted_dmg_paths:
            raise RuntimeError(
                f"Eject mounted '{BUILD_SETTINGS['app_name']}' installer volumes"
                f" from your system: {repr(mounted_dmg_paths)}"
            )

if __name__ == "__main__":
    verify_supported_platform()
    cli()
