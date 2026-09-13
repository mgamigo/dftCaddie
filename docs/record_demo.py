"""Record the README demo using the real CLI in a temporary calculation folder.

Run from the checkout with:
    uv run --with pexpect --with pyte --with pillow python /path/to/assets/docs/record_demo.py /path/to/dftCaddie

Functions
---------
main()
    Drive an interactive preparation and render terminal frames into a GIF.
"""

import os
from pathlib import Path
import shutil
import sys
import tempfile
import time

import pexpect
from PIL import Image, ImageDraw, ImageFont
import pyte
from ase.io import read


def main():
    """Capture typed choices and preparation output with bundled resources."""
    root = Path(sys.argv[1]).resolve()
    output = Path(__file__).resolve().parent / "assets/interactive.gif"
    output.parent.mkdir(parents=True, exist_ok=True)
    font = ImageFont.truetype("DejaVuSansMono.ttf", 16)
    # Noto's bitmap emoji font has a fixed strike size; scale its rendered glyph.
    emoji_font = ImageFont.truetype("NotoColorEmoji.ttf", 109)
    golf = "\u26f3"
    bounds = emoji_font.getbbox(golf)
    emoji = Image.new("RGBA", (bounds[2] - bounds[0], bounds[3] - bounds[1]))
    ImageDraw.Draw(emoji).text(
        (-bounds[0], -bounds[1]), golf, font=emoji_font, embedded_color=True
    )
    emoji.thumbnail((20, 20), Image.Resampling.LANCZOS)
    columns, rows = 88, 15
    cell_width = font.getlength("M")
    screen = pyte.Screen(columns, rows)
    stream = pyte.Stream(screen)
    frames = []
    durations = []

    def frame(duration=160):
        """Render the current terminal screen and retain its display duration."""
        image = Image.new("RGB", (928, 383), "#171b20")
        draw = ImageDraw.Draw(image)
        draw.rectangle((0, 0, 928, 42), fill="#293138")
        draw.text(
            (24, 10), "dftCaddie  /  interactive preparation", font=font, fill="#78d9b0"
        )
        for row in range(rows):
            for column in range(columns):
                char = screen.buffer[row][column].data
                x, y = 24 + column * cell_width, 52 + row * 21
                if char == golf:
                    image.paste(emoji, (round(x), y), emoji)
                elif char.strip():
                    draw.text((x, y), char, font=font, fill="#e8edf0")
        frames.append(image)
        durations.append(duration)

    with tempfile.TemporaryDirectory(prefix="caddie-demo-") as work:
        shutil.copy(root / "tests/data/Si.cif", Path(work) / "Si.cif")
        # Force bundled resources without reading or modifying the user's config.
        program = (
            "from functools import partial; "
            "from dftcaddie import config; "
            "config.load_config = partial(config.load_config, default_config=True); "
            "from dftcaddie.cli import main; "
            "raise SystemExit(main(['calc', '--details', '--structure', 'Si.cif']))"
        )
        stream.feed("$ caddie calc --details --structure Si.cif\r\n")
        frame(1000)
        child = pexpect.spawn(
            sys.executable,
            ["-c", program],
            cwd=work,
            env={**os.environ, "TERM": "xterm-256color", "PROMPT_TOOLKIT_NO_CPR": "1"},
            encoding="utf-8",
            dimensions=(rows, columns),
        )
        transcript = ""

        def read_for(seconds):
            """Feed real PTY output into the terminal emulator for a short interval."""
            nonlocal transcript
            deadline = time.monotonic() + seconds
            while time.monotonic() < deadline:
                try:
                    chunk = child.read_nonblocking(65536, timeout=0.1)
                except pexpect.TIMEOUT:
                    continue
                except pexpect.EOF:
                    break
                transcript += chunk
                stream.feed(chunk)

        def wait_for(label):
            """Wait for a real CLI prompt before supplying its answer."""
            deadline = time.monotonic() + 15
            while label not in "\n".join(screen.display):
                read_for(0.2)
                if time.monotonic() > deadline:
                    raise RuntimeError(f"Demo did not reach {label!r}: {transcript}")
            read_for(0.3)
            frame(1400)

        try:
            for label, answer in [
                ("Select calculation:", "ban"),
                ("Select code:", "quantum"),
                ("Spin", "n"),
            ]:
                wait_for(label)
                for char in answer:
                    child.send(char)
                    read_for(0.15)
                    frame()
                frame(650)
                child.send("\r")
                read_for(0.4)
            child.expect(pexpect.EOF, timeout=20)
            stream.feed(child.before)
            child.close()
            if child.exitstatus != 0:
                raise RuntimeError("Interactive preparation failed")
            assert (Path(work) / "SYSTEM.INFO").is_file()
            nat = len(read(Path(work) / "Si.cif"))
            assert f"ATM_NUM={nat}" in (Path(work) / "SYSTEM.INFO").read_text()
            frame(3500)
        finally:
            child.close(force=True)

    frames[0].save(
        output,
        save_all=True,
        append_images=frames[1:],
        duration=durations,
        loop=0,
        optimize=True,
    )
    print(output)


if __name__ == "__main__":
    main()
