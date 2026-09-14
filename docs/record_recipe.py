"""Render a recipe walkthrough from bundled YAML and a prepared master script.

Functions
---------
main()
    Prepare a temporary QE bands workflow and render its configuration tour.
render(title, caption, source, start, count, lexer, highlight)
    Render a numbered source excerpt with syntax coloring and a highlighted row.
"""

from pathlib import Path
import subprocess
import sys
import tempfile

from PIL import Image, ImageDraw, ImageFont
from pygments import lex
from pygments.lexers import BashLexer, YamlLexer
from pygments.styles import get_style_by_name


def render(title, caption, source, start, count, lexer, highlight):
    """Render an excerpt of an actual source file.

    Parameters
    ----------
    title, caption : str
        File label and explanation displayed above and below the source.
    source : str
        Complete source file contents.
    start, count : int
        Zero-based first source line and maximum number of lines to display.
    lexer : pygments.lexer.Lexer
        Syntax lexer for the displayed file.
    highlight : str
        Text identifying rows to emphasize.

    Returns
    -------
    PIL.Image.Image
        A fixed-size frame with legible, syntax-colored source.
    """
    font = ImageFont.truetype("DejaVuSansMono.ttf", 18)
    label_font = ImageFont.truetype("DejaVuSans.ttf", 18)
    style = get_style_by_name("monokai")
    frame = Image.new("RGB", (1040, 490), "#171b20")
    draw = ImageDraw.Draw(frame)
    draw.rectangle((0, 0, 1040, 46), fill="#293138")
    draw.text((24, 12), title, font=font, fill="#78d9b0")
    lines = source.splitlines()[start : start + count]
    for row, line in enumerate(lines):
        y = 62 + row * 24
        if highlight in line:
            draw.rectangle((66, y - 2, 1016, y + 22), fill="#2d383c")
        draw.text((22, y), str(start + row + 1).rjust(3), font=font, fill="#879299")
        x = 84
        for token, value in lex(line, lexer):
            value = value.rstrip("\n")
            while token not in style.styles:
                token = token.parent
            color = style.style_for_token(token)["color"] or "e8edf0"
            draw.text((x, y), value, font=font, fill="#" + color)
            x += font.getlength(value)
        assert x < 1016, f"Source line exceeds the viewport: {line}"
    draw.line((24, 442, 1016, 442), fill="#384249")
    draw.text((24, 458), caption, font=label_font, fill="#e8edf0")
    return frame


def main():
    """Render three scenes using real recipe and generated workflow contents.

    Notes
    -----
    Run from a development checkout with Pillow and Pygments installed.
    Preparation uses bundled resources and the local cluster preset in a
    temporary directory. No user configuration is changed and no job is run.
    """
    from dftcaddie.config import load_config

    _, resources = load_config(default_config=True)
    source = (resources / "config.yaml").read_text()
    with tempfile.TemporaryDirectory(prefix="caddie-recipe-demo-") as work:
        program = (
            "from functools import partial; "
            "from dftcaddie import config, utils; "
            "config.load_config = partial(config.load_config, default_config=True); "
            "utils.resolve_cluster = lambda clusters: 'local'; "
            "from dftcaddie.cli import main; "
            "raise SystemExit(main(['calc', '--kind', 'bands', "
            "'--code', 'quantum_espresso']))"
        )
        subprocess.run(
            [sys.executable, "-c", program],
            cwd=work,
            check=True,
            capture_output=True,
            text=True,
        )
        master = (Path(work) / "master.sh").read_text()
        jobs = ["bash scf.sh", "bash bands.sh", "bash project_bands.sh"]
        assert all(job in master for job in jobs)
        assert [master.index(job) for job in jobs] == sorted(
            master.index(job) for job in jobs
        )

    lines = source.splitlines()
    bands = lines.index("  bands:")
    files = lines.index("    files:", bands)
    job_start = next(
        i for i, line in enumerate(master.splitlines()) if "#Load system" in line
    )
    frames = [
        render(
            "01 / config.yaml / choices and defaults",
            "Choose which settings to expose and which defaults to apply.",
            source,
            bands,
            14,
            YamlLexer(),
            "default:",
        ),
        render(
            "02 / config.yaml / template mapping",
            "Select the input files. List shell scripts in execution order.",
            source,
            files,
            14,
            YamlLexer(),
            "quantum_espresso/",
        ),
        render(
            "03 / generated master.sh / the resulting workflow",
            "caddie calc --kind bands --code quantum_espresso",
            master,
            job_start,
            13,
            BashLexer(),
            "bash ",
        ),
    ]
    output = Path(__file__).resolve().parent / "assets"
    output.mkdir(parents=True, exist_ok=True)
    frames[0].save(
        output / "recipe.gif",
        save_all=True,
        append_images=frames[1:],
        duration=[5000, 5000, 4500],
        loop=0,
        optimize=True,
    )
    for name, frame in zip(
        ("recipe-defaults", "recipe-files", "recipe-result"), frames
    ):
        frame.save(output / f"{name}.png")
    print(output / "recipe.gif")


if __name__ == "__main__":
    main()
