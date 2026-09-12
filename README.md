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
succeeded. It requires the DejaVu Sans Mono font. No DFT calculation is run.
The output replaces the GIF beside the recorder in this branch.
