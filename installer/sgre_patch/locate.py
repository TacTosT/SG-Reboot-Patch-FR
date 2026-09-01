"""Find the STEINS;GATE RE:BOOT data folder on someone else's machine.

The dev box hard-codes one path; a redistributable patcher cannot. Steam's own
bookkeeping is the reliable source: the registry says where Steam lives,
`libraryfolders.vdf` says where its other libraries live, and each library
holds `steamapps/common/<folder>/wind3d11data`.
"""
import os
import re

APP_ID = "4012810"
GAME_FOLDERS = ("SGRE", "STEINS;GATE RE:BOOT", "STEINSGATE RE BOOT")
DATA_DIR = "wind3d11data"
REQUIRED = ("scenario_info.psb.m", "scenario_body.bin")


def is_game_dir(path) -> bool:
    """True if `path` is the wind3d11data folder of a real install."""
    return bool(path) and all(os.path.isfile(os.path.join(path, f)) for f in REQUIRED)


def normalize(path):
    """Accept the data folder, the game folder, or a Steam library root."""
    if not path:
        return None
    path = os.path.abspath(path)
    if is_game_dir(path):
        return path
    for probe in (
        os.path.join(path, DATA_DIR),
        os.path.join(path, "SGRE", DATA_DIR),
        os.path.join(path, "common", "SGRE", DATA_DIR),
        os.path.join(path, "steamapps", "common", "SGRE", DATA_DIR),
    ):
        if is_game_dir(probe):
            return probe
    # Last resort: a shallow walk, in case the folder was renamed.
    for root, dirs, _ in os.walk(path):
        if root.count(os.sep) - path.count(os.sep) > 3:
            dirs[:] = []
            continue
        if os.path.basename(root) == DATA_DIR and is_game_dir(root):
            return root
    return None


def _steam_roots():
    roots = []
    try:
        import winreg
        for hive, key, value in (
            (winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam", "SteamPath"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam", "InstallPath"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Valve\Steam", "InstallPath"),
        ):
            try:
                with winreg.OpenKey(hive, key) as k:
                    roots.append(os.path.normpath(winreg.QueryValueEx(k, value)[0]))
            except OSError:
                pass
    except ImportError:
        pass
    roots += [
        r"C:\Program Files (x86)\Steam",
        r"C:\Program Files\Steam",
        os.path.expanduser(r"~\Steam"),
    ]
    seen, out = set(), []
    for r in roots:
        low = r.lower()
        if low not in seen and os.path.isdir(r):
            seen.add(low)
            out.append(r)
    return out


def _libraries(steam_root):
    """Every library path Steam knows about, the main one first."""
    libs = [steam_root]
    for vdf in (os.path.join(steam_root, "steamapps", "libraryfolders.vdf"),
                os.path.join(steam_root, "config", "libraryfolders.vdf")):
        try:
            with open(vdf, encoding="utf-8", errors="replace") as f:
                text = f.read()
        except OSError:
            continue
        libs += [p.replace("\\\\", "\\")
                 for p in re.findall(r'"path"\s+"([^"]+)"', text)]
    seen, out = set(), []
    for p in libs:
        low = os.path.normpath(p).lower()
        if low not in seen:
            seen.add(low)
            out.append(os.path.normpath(p))
    return out


def candidates():
    """All plausible data folders, best guess first."""
    found = []

    def add(path):
        if is_game_dir(path) and path not in found:
            found.append(path)

    env = os.environ.get("SGRE_DIR")
    if env:
        add(os.path.abspath(env))

    for steam_root in _steam_roots():
        for lib in _libraries(steam_root):
            common = os.path.join(lib, "steamapps", "common")
            for folder in GAME_FOLDERS:
                add(os.path.join(common, folder, DATA_DIR))
            # The manifest names the install folder, whatever Steam called it.
            manifest = os.path.join(lib, "steamapps", f"appmanifest_{APP_ID}.acf")
            try:
                with open(manifest, encoding="utf-8", errors="replace") as f:
                    m = re.search(r'"installdir"\s+"([^"]+)"', f.read())
                if m:
                    add(os.path.join(common, m.group(1), DATA_DIR))
            except OSError:
                pass

    for drive in "CDEFGH":
        add(rf"{drive}:\SteamLibrary\steamapps\common\SGRE\{DATA_DIR}")

    return found


def autodetect():
    found = candidates()
    return found[0] if found else None
