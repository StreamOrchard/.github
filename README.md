# StreamOrchard/.github

The **StreamOrchard** organization's profile. GitHub shows [`profile/README.md`](profile/README.md) at the top of
[github.com/StreamOrchard](https://github.com/StreamOrchard).

## The artwork

The images in `profile/` are animated SVGs drawn by `scripts/build.py`. Don't edit them by hand: change the script and
run it again.

```sh
python3 -m venv .venv && .venv/bin/pip install fonttools brotli uharfbuzz
.venv/bin/python scripts/build.py
```

- **Text is drawn as outlines** from the fonts in `scripts/fonts` (Inter and JetBrains Mono, both under the SIL Open
  Font License), because an SVG shown as an image can't load fonts.
- **The app icons** in `scripts/icons` are copied from the apps and from
  [StreamOrchard/brand](https://github.com/StreamOrchard/brand). The colors are the brand's.
- **The animations** are CSS and SMIL, which GitHub plays in a README. The CSS ones stop for visitors who ask for
  reduced motion.
