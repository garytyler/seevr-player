import os
from glob import glob
from os.path import commonpath, dirname, join, relpath

from PyInstaller.compat import is_darwin, is_linux, is_win

if is_linux:
    DYLIB_PATTERN = "*.dylib"
elif is_win:
    DYLIB_PATTERN = "*.dll"
elif is_darwin:
    DYLIB_PATTERN = "lib*.so"


def hook(hook_api):
    if not hook_api.__name__ == "vlc":
        return None

    libvlc_src_file = os.environ["PYTHON_VLC_LIB_PATH"]
    plugin_src_dir = os.environ["PYTHON_VLC_MODULE_PATH"]

    # Get common root
    common_root = commonpath([libvlc_src_file, plugin_src_dir])

    # Add libvlc binaries
    libvlc_src_files = glob(join(dirname(libvlc_src_file), DYLIB_PATTERN))
    libvlc_binaries = []
    for f in libvlc_src_files:
        binary_tuple = (f, "vlc")
        libvlc_binaries.append(binary_tuple)
    hook_api.add_binaries(libvlc_binaries)

    # Add plugin binaries
    plugin_src_files = []
    for root, _, __ in os.walk(plugin_src_dir):
        plugin_src_files.extend(glob(join(root, DYLIB_PATTERN)))
    plugin_binaries = []
    for f in plugin_src_files:
        rel_dir = relpath(dirname(f), common_root)
        bin_tuple = (f, rel_dir)
        plugin_binaries.append(bin_tuple)
    hook_api.add_binaries(plugin_binaries)
