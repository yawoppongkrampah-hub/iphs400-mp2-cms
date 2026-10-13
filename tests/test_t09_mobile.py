"""T09: phone width, measured in a real browser, and screenshots taken at real widths.

`scripts/admin_screenshots.py` starts the console on a throwaway seeded database,
loads every admin screen in headless Chrome at 390 px and 1280 px, and measures
whether the page is wider than the screen. The browser test is skipped when Chrome
is not installed; the screenshot-file test needs no browser.
"""
import struct
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SHOTS = ROOT / "docs" / "screenshots"
SCREENS = ["login", "dashboard", "content-list", "editor", "users", "editor-denied"]
NO_BROWSER = 77


def png_size(path):
    header = path.read_bytes()[:24]
    assert header[:8] == b"\x89PNG\r\n\x1a\n", f"{path.name} is not a PNG"
    return struct.unpack(">II", header[16:24])


def test_no_admin_screen_is_wider_than_a_390_px_phone():
    result = subprocess.run([sys.executable, str(ROOT / "scripts" / "admin_screenshots.py"),
                             "--check-only"], capture_output=True, text=True, timeout=240)
    if result.returncode == NO_BROWSER:
        pytest.skip("Chrome is not installed")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "390 px" in result.stdout and "OVERFLOW" not in result.stdout


@pytest.mark.parametrize("screen", SCREENS)
@pytest.mark.parametrize("width", [1280, 390])
def test_each_required_screenshot_is_a_full_page_at_its_real_width(screen, width):
    path = SHOTS / f"{screen}-{width}.png"
    assert path.exists(), f"missing {path.name}"
    pixel_width, pixel_height = png_size(path)
    # A page that overflowed would make a wider image, because the script never crops
    # narrower than the page. A width that equals the viewport means it fitted.
    assert pixel_width == width, f"{path.name} is {pixel_width} px wide"
    assert pixel_height >= 400, f"{path.name} is only {pixel_height} px tall"
