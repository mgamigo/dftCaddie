# dftCaddie demo assets

This branch contains documentation media separately from the application source.
The main README links to `docs/assets/interactive.gif` on this branch.

To regenerate the recording, run this from a development checkout of dftCaddie:

```bash
uv run --with pexpect --with pyte --with pillow \
    python /path/to/assets/docs/record_demo.py "$PWD"
```

The recorder drives the real CLI through a pseudo-terminal, uses bundled
configuration in a temporary folder, and checks that structure insertion
succeeded. It requires DejaVu Sans Mono and Noto Color Emoji fonts. The terminal
viewport is 88 columns by 15 rows, rendered at 928 by 383 pixels. The closing
golf emoji uses the color font while terminal text uses the monospace font.
No DFT calculation is run.
The output replaces the GIF beside the recorder in this branch.

The main README also uses a syntax-colored recipe walkthrough.
It shows excerpts of the bundled configuration followed
by an actual generated `master.sh`, with static frames for readers who prefer
to avoid animation:

```bash
uv run --with pillow --with pygments python assets/docs/record_recipe.py
```

Run this from the development checkout. It uses the local cluster preset in
a temporary directory and requires DejaVu Sans and DejaVu Sans Mono fonts.
The output is `docs/assets/recipe.gif` and three `recipe-*.png` stills.
It neither changes user resources nor executes the prepared calculation.
The final frame starts at `#Load system` so that loading `SYSTEM.INFO` is
visible before the workflow script calls.

`docs/assets/workflow.svg` is the editable vector diagram used in the main
README's "From Templates to a Job" section. It needs no generation step.
