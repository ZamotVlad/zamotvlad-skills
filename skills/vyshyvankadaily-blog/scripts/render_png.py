#!/usr/bin/env python3
"""Рендер HTML/SVG у PNG точного розміру через headless Chromium.

    python3 render_png.py schema.html out.png --width 1200 --height 676

Вікно береться вищим за потрібне (headless з'їдає частину висоти), потім
кадр обрізається до width x height. Потрібен Pillow і Chromium.
"""

import argparse
import glob
import os
import shutil
import subprocess
import sys
import tempfile


def find_chrome():
    env = os.environ.get("CHROME")
    if env:
        return env
    for pattern in ("/opt/pw-browsers/chromium*/chrome-linux*/chrome",):
        hits = sorted(glob.glob(pattern))
        if hits:
            return hits[-1]
    for name in ("chromium", "chromium-browser", "google-chrome", "chrome"):
        path = shutil.which(name)
        if path:
            return path
    sys.exit("Chromium не знайдено: задайте змінну CHROME")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("out")
    ap.add_argument("--width", type=int, required=True)
    ap.add_argument("--height", type=int, required=True)
    a = ap.parse_args()
    from PIL import Image

    tmp = tempfile.mktemp(suffix=".png")
    subprocess.run(
        [find_chrome(), "--headless", "--no-sandbox", "--hide-scrollbars", "--allow-file-access-from-files",
         f"--window-size={a.width},{a.height + 200}", f"--screenshot={tmp}", "file://" + os.path.abspath(a.src)],
        check=True, capture_output=True,
    )
    im = Image.open(tmp)
    if im.size[1] < a.height:
        sys.exit(f"Кадр {im.size} нижчий за потрібну висоту {a.height}")
    im.crop((0, 0, a.width, a.height)).save(a.out)
    os.remove(tmp)
    print(f"{a.out}: {a.width}x{a.height}")


if __name__ == "__main__":
    main()
