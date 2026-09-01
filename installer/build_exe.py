"""Build the redistributable: one .exe, plus a .zip ready to hand out.

    python build_exe.py

Produces
    dist/Patch_FR_SteinsGate_ReBoot.exe      what people download
    dist/SteinsGate_ReBoot_Patch_FR_<v>.zip  the exe + the readme

The French text (data/all_fr.jsonl) is baked into the exe, so the zip is also a
complete off-site copy of the translation.
"""
import os
import shutil
import subprocess
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from patcher import VERSION                                       # noqa: E402

NAME = "Patch_FR_SteinsGate_ReBoot"
ICON = os.path.join(HERE, "icon.ico")


def make_icon():
    """A small amber-on-dark tile, so the exe is not a blank window icon."""
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return None
    sizes = [16, 24, 32, 48, 64, 128, 256]
    base = Image.new("RGBA", (256, 256), (20, 22, 28, 255))
    d = ImageDraw.Draw(base)
    d.rounded_rectangle([10, 10, 246, 246], radius=40, fill=(28, 31, 40, 255),
                        outline=(224, 163, 62, 255), width=8)
    # Divergence-meter wink: a needle sweeping across the tile.
    d.line([(48, 196), (208, 76)], fill=(224, 163, 62, 255), width=14)
    d.ellipse([38, 186, 62, 210], fill=(224, 163, 62, 255))
    d.text((92, 96), "FR", fill=(230, 232, 238, 255),
           font=_font(72), anchor="mm")
    base.save(ICON, sizes=[(s, s) for s in sizes])
    return ICON


def _font(size):
    from PIL import ImageFont
    for name in ("segoeuib.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def main():
    icon = make_icon()
    cmd = [
        sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean",
        "--onefile", "--windowed", "--name", NAME,
        "--add-data", os.path.join(HERE, "data", "all_fr.jsonl") + os.pathsep + "data",
        "--add-data", ICON + os.pathsep + ".",
        "--exclude-module", "numpy",
        "--exclude-module", "matplotlib",
        "--exclude-module", "PIL",
        "--exclude-module", "pytest",
        "--distpath", os.path.join(HERE, "dist"),
        "--workpath", os.path.join(HERE, "build"),
        "--specpath", os.path.join(HERE, "build"),
    ]
    if icon:
        cmd += ["--icon", icon]
    cmd.append(os.path.join(HERE, "patcher.py"))

    print(" ".join(cmd))
    subprocess.check_call(cmd, cwd=HERE)

    exe = os.path.join(HERE, "dist", NAME + ".exe")
    zip_path = os.path.join(HERE, "dist",
                            "SteinsGate_ReBoot_Patch_FR_v%s.zip" % VERSION)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(exe, NAME + ".exe")
        readme = os.path.join(HERE, "LISEZMOI.txt")
        if os.path.exists(readme):
            z.write(readme, "LISEZMOI.txt")
    print("\nexe :", exe, "(%.1f Mo)" % (os.path.getsize(exe) / 1e6))
    print("zip :", zip_path, "(%.1f Mo)" % (os.path.getsize(zip_path) / 1e6))


if __name__ == "__main__":
    main()
