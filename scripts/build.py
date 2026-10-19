#!/usr/bin/env python3
"""Draws the organization profile's artwork: profile/hero.svg and one panel per app.

The text is drawn as outlines from the fonts in scripts/fonts, so it looks the same on every computer (an SVG shown
as an image can't load fonts). The animations are CSS and SMIL, which GitHub shows in a README.

    python3 -m venv .venv && .venv/bin/pip install fonttools brotli uharfbuzz
    .venv/bin/python scripts/build.py
"""
import io
import random
import re
from pathlib import Path

import uharfbuzz as hb
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'profile'
ICONS = ROOT / 'scripts' / 'icons'

# The brand's colors (StreamOrchard/brand README).
LIME, GREEN, TEAL, GRID = '#c4ff5c', '#4cf56a', '#14c79a', '#3dff8a'
TEXT, MID, DIM = '#eef3ef', '#a9b8ae', '#7d8c83'
KICK, TWITCH, YOUTUBE = '#53fc18', '#a970ff', '#ff4e45'
AMBER, VIOLET = '#f5b942', '#a78bfa'


# ---------------------------------------------------------------- text as outlines

def _face(name):
    font = TTFont(ROOT / 'scripts' / 'fonts' / name)
    font.flavor = None
    data = io.BytesIO()
    font.save(data)
    return hb.Face(data.getvalue()), font['head'].unitsPerEm


FACES = {'sans': _face('InterVariable-latin.woff2'), 'mono': _face('JetBrainsMono-latin.woff2')}
_fonts = {}


def num(v):
    s = f'{v:.1f}'
    return s[:-2] if s.endswith('.0') else s


def _font(family, wght, size):
    axes = {'wght': wght}
    if family == 'sans':
        axes['opsz'] = max(14, min(32, size))  # Inter Display at large sizes
    key = (family, tuple(sorted(axes.items())))
    if key not in _fonts:
        font = hb.Font(FACES[family][0])
        font.set_variations(axes)
        _fonts[key] = font
    return _fonts[key]


def _runs(runs, wght, fill):
    return [(runs, wght, fill)] if isinstance(runs, str) else runs


def _layout(runs, size, family, track):
    upem = FACES[family][1]
    scale, gap, x, out = size / upem, track * size, 0.0, []
    for s, wght, fill in runs:
        font = _font(family, wght, size)
        buf = hb.Buffer()
        buf.add_str(s)
        buf.guess_segment_properties()
        hb.shape(font, buf, {'kern': True, 'liga': True, 'calt': True})
        glyphs = []
        for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
            glyphs.append((info.codepoint, x + pos.x_offset * scale, -pos.y_offset * scale))
            x += pos.x_advance * scale + gap
        out.append((font, glyphs, fill))
    return out, scale, x - gap


def textw(runs, size, wght=400, family='sans', track=0.0):
    return _layout(_runs(runs, wght, None), size, family, track)[2]


def text(runs, x, y, size, wght=400, fill=TEXT, anchor='start', family='sans', track=0.0, attrs=''):
    """Text as <path>s. `runs` is a string, or [(text, weight, fill), ...] for mixed weights on one line."""
    laid, scale, width = _layout(_runs(runs, wght, fill), size, family, track)
    x0 = x - {'start': 0, 'middle': width / 2, 'end': width}[anchor]
    paths = []
    for font, glyphs, color in laid:
        pen = SVGPathPen(None, ntos=num)
        for gid, gx, gy in glyphs:
            font.draw_glyph_with_pen(gid, TransformPen(pen, (scale, 0, 0, -scale, gx, gy)))
        d = pen.getCommands()
        if d:
            paths.append(f'<path fill="{color}" d="{d}"/>')
    return f'<g transform="translate({num(x0)} {num(y)})"{attrs}>{"".join(paths)}</g>'


def wrap(s, size, width, wght=400):
    lines, line = [], ''
    for word in s.split():
        trial = f'{line} {word}'.strip()
        if line and textw(trial, size, wght) > width:
            lines.append(line)
            line = word
        else:
            line = trial
    return lines + [line]


# ---------------------------------------------------------------- shared pieces

def icon(name, prefix, x, y, size, viewbox='0 0 512 512'):
    """One of scripts/icons as a nested <svg>, its ids prefixed so several can share a file."""
    src = (ICONS / f'{name}.svg').read_text()
    body = re.sub(r'^.*?<svg[^>]*>|</svg>\s*$', '', src, flags=re.S)
    body = re.sub(r'<!--.*?-->', '', body, flags=re.S)
    body = re.sub(r'id="([^"]+)"', rf'id="{prefix}-\1"', body)
    body = re.sub(r'url\(#([^)]+)\)', rf'url(#{prefix}-\1)', body)
    return f'<svg x="{num(x)}" y="{num(y)}" width="{num(size)}" height="{num(size)}" viewBox="{viewbox}">{body}</svg>'


PEAR = ('M512 252C447 252 413.2 306.6 413.2 371.6C413.2 426.2 382 457.4 343 504.2C298.8 556.2 267.6 608.2 267.6 670.6'
        'C267.6 795.4 374.2 870.8 512 870.8C649.8 870.8 756.4 795.4 756.4 670.6C756.4 608.2 725.2 556.2 681 504.2'
        'C642 457.4 610.8 426.2 610.8 371.6C610.8 306.6 577 252 512 252Z')
PEAR_STEM = 'M512 262.4C512 220.8 525 184.4 548.4 158.4'
PEAR_LEAF = 'M553.6 200C579.6 140.2 652.4 122 709.6 140.2C691.4 200 623.8 231.2 553.6 200Z'
DROP = 'M512 176C602 292 770 462 770 640a258 258 0 0 1-516 0C254 462 422 292 512 176Z'


def multiview_icon(prefix, x, y, size):
    """Stream Multiview's pear on the same tile as the other icons (the app's own icon is a bare pear)."""
    p = prefix
    return f'''<svg x="{num(x)}" y="{num(y)}" width="{num(size)}" height="{num(size)}" viewBox="0 0 512 512"><defs>
<linearGradient id="{p}-bg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#121a15"/><stop offset="1" stop-color="#060908"/></linearGradient>
<radialGradient id="{p}-glow" cx=".5" cy=".55" r=".6"><stop offset="0" stop-color="{KICK}" stop-opacity=".3"/><stop offset="1" stop-color="{KICK}" stop-opacity="0"/></radialGradient>
<linearGradient id="{p}-pear" x1=".2" y1="0" x2=".8" y2="1"><stop offset="0" stop-color="#b6ff8f"/><stop offset=".45" stop-color="{KICK}"/><stop offset="1" stop-color="#1fae06"/></linearGradient>
<filter id="{p}-soft" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="14"/></filter></defs>
<rect width="512" height="512" rx="112" fill="url(#{p}-bg)"/><rect width="512" height="512" rx="112" fill="url(#{p}-glow)"/>
<rect x="1" y="1" width="510" height="510" rx="111" fill="none" stroke="{GRID}" stroke-opacity=".14" stroke-width="2"/>
<g transform="translate(256 262) scale(.5) translate(-512 -515)">
<path d="{PEAR}" fill="url(#{p}-pear)" opacity=".55" filter="url(#{p}-soft)"/>
<path d="{PEAR}" fill="url(#{p}-pear)"/><path d="{PEAR_STEM}" stroke="#2fd36b" stroke-width="40" stroke-linecap="round" fill="none"/>
<path d="{PEAR_LEAF}" fill="#7dfa7a"/><path d="M372 560c-26 40-38 82-36 124" stroke="#fff" stroke-opacity=".45" stroke-width="30" stroke-linecap="round" fill="none"/></g></svg>'''


def card(w, h, glow=(.5, .3)):
    """The night background every image sits on, with the faint grid from the Grapevine artwork."""
    return f'''<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#101813"/><stop offset="1" stop-color="#050807"/></linearGradient>
<radialGradient id="bgglow" cx="{glow[0]}" cy="{glow[1]}" r=".65"><stop offset="0" stop-color="{GRID}" stop-opacity=".13"/><stop offset="1" stop-color="{GRID}" stop-opacity="0"/></radialGradient>
<pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse"><path d="M40 0H0V40" fill="none" stroke="{GRID}" stroke-opacity=".035"/></pattern>
<linearGradient id="fruit" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{LIME}"/><stop offset=".5" stop-color="{GREEN}"/><stop offset="1" stop-color="{TEAL}"/></linearGradient>
<clipPath id="cardclip"><rect width="{w}" height="{h}" rx="28"/></clipPath>
</defs>
<rect width="{w}" height="{h}" rx="28" fill="url(#bg)"/><rect width="{w}" height="{h}" rx="28" fill="url(#bgglow)"/>
<rect width="{w}" height="{h}" rx="28" fill="url(#grid)"/>
<rect x=".75" y=".75" width="{w - 1.5}" height="{h - 1.5}" rx="27.25" fill="none" stroke="{GRID}" stroke-opacity=".12" stroke-width="1.5"/>'''


def svg(w, h, title, style, defs, body):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-label="{title}">
<title>{title}</title>
<style>{style}
@media (prefers-reduced-motion: reduce) {{ * {{ animation: none !important; }} }}</style>
<defs>{defs}{card(w, h) if 'id="bg"' not in defs else ''}
{body}
</svg>
'''


def pill(x, y, label, dot):
    w = 36 + textw(label, 15, 600) + 18
    return (f'<rect x="{num(x)}" y="{y}" width="{num(w)}" height="36" rx="18" fill="#fff" fill-opacity=".035" '
            f'stroke="#fff" stroke-opacity=".1"/><circle cx="{num(x + 20)}" cy="{y + 18}" r="5" fill="{dot}"/>'
            + text(label, x + 34, y + 23.5, 15, 600, TEXT)), w


def pills(x, y, items):
    out = []
    for label, dot in items:
        s, w = pill(x, y, label, dot)
        out.append(s)
        x += w + 12
    return ''.join(out)


def blurb(x, eyebrow, name, lines, items, icon_svg):
    """The words on a panel: icon and eyebrow, the app's name, two or three lines about it, and pills."""
    out = [icon_svg, text(eyebrow, x + 68, 90, 13, 700, LIME, track=.14)]
    if isinstance(name, tuple):  # two lines, like the apps' own artwork
        out += [text(name[0], x - 3, 176, 60, 800, TEXT, track=-.025),
                text(name[1], x - 3, 240, 60, 800, 'url(#fruit)', track=-.025)]
        top = 290
    else:
        out.append(text(name, x - 4, 210, 76, track=-.035))
        top = 262
    for i, line in enumerate(lines):
        out.append(text(line, x, top + i * 29, 20, 400, MID))
    out.append(pills(x, top + len(lines) * 29 + 12, items))
    return ''.join(out)


# ---------------------------------------------------------------- hero

def hero():
    W, H, HZ = 1280, 560, 352
    rnd = random.Random(7)
    flies = []
    for i in range(26):
        x, y = rnd.uniform(40, W - 40), rnd.uniform(44, HZ - 10)
        if 330 < x < 950 and 40 < y < 320:  # keep the name clear
            y = rnd.choice([rnd.uniform(44, 60), rnd.uniform(318, HZ - 6)])
        r = rnd.uniform(1.2, 2.6)
        flies.append(f'<g class="f" style="animation-delay:-{rnd.uniform(0, 9):.1f}s;animation-duration:{rnd.uniform(7, 12):.1f}s">'
                     f'<circle cx="{num(x)}" cy="{num(y)}" r="{num(r * 4)}" fill="url(#fly)"/>'
                     f'<circle cx="{num(x)}" cy="{num(y)}" r="{num(r)}" fill="{LIME}"/></g>')

    verticals = ''.join(f'<path d="M{num(640 + k * 30)} {HZ}L{num(640 + k * 300)} {H}"/>' for k in range(-24, 25))
    rows = ''.join(f'<path class="h" d="M0 {HZ}H{W}" style="animation-delay:-{i * 0.75:.2f}s"/>' for i in range(8))

    apps = [('Stream Multiview', 400, 'mv'), ('Grapevine', 640, 'gv'), ('Pear Drops', 880, 'pd')]
    S, TOP = 72, 384
    icons, labels = [], []
    for label, cx, key in apps:
        x = cx - S / 2
        art = {'mv': multiview_icon('h-mv', x, TOP, S), 'gv': icon('grapevine', 'h-gv', x, TOP, S),
               'pd': icon('pear-drops', 'h-pd', x, TOP, S, '100 100 824 824')}[key]
        icons.append(f'<g id="app-{key}">{art}</g>')
        # its reflection in the glass floor
        icons.append(f'<use href="#app-{key}" transform="translate(0 {2 * (TOP + S) + 4}) scale(1 -1)" mask="url(#reflect)" opacity=".6"/>')
        icons.append(f'<ellipse cx="{cx}" cy="{TOP + S + 2}" rx="46" ry="6" fill="{GRID}" opacity=".22" filter="url(#blur6)"/>')
        labels.append(text(label, cx, 536, 15, 600, MID, 'middle'))

    vine = 'M436 420C486 446 560 396 640 420C720 444 794 394 844 420'
    pulses = ''.join(
        f'<g><circle r="9" fill="url(#fly)"/><circle r="3.2" fill="{c}"/>'
        f'<animateMotion dur="{d}s" begin="{b}s" repeatCount="indefinite" keyPoints="{kp}" keyTimes="0;1" calcMode="linear"><mpath href="#vine"/></animateMotion></g>'
        for c, d, b, kp in [(LIME, 3.2, 0, '0;1'), (LIME, 3.2, -1.6, '0;1'), (TEAL, 4.1, -.7, '1;0')])

    style = f'''
.h {{ stroke: {GRID}; animation: h 6s cubic-bezier(.62,0,.92,.55) infinite; }}
@keyframes h {{ from {{ transform: translateY(0); opacity: 0; }} 30% {{ opacity: .5; }} to {{ transform: translateY({H - HZ}px); opacity: 1; }} }}
.f {{ animation: f 9s ease-in-out infinite; }}
@keyframes f {{ 0% {{ opacity: 0; transform: translate(0, 0); }} 25% {{ opacity: .9; }} 55% {{ opacity: .35; }}
  80% {{ opacity: .85; }} 100% {{ opacity: 0; transform: translate(12px, -30px); }} }}
.beat {{ transform-box: fill-box; transform-origin: center; animation: beat 3.2s ease-in-out infinite; }}
@keyframes beat {{ 0%, 100% {{ opacity: .25; transform: scale(.85); }} 50% {{ opacity: .8; transform: scale(1.2); }} }}
.horizon {{ animation: hz 6s ease-in-out infinite; }}
@keyframes hz {{ 0%, 100% {{ opacity: .55; }} 50% {{ opacity: .9; }} }}'''

    defs = f'''<radialGradient id="fly"><stop offset="0" stop-color="{LIME}" stop-opacity=".55"/><stop offset="1" stop-color="{LIME}" stop-opacity="0"/></radialGradient>
<linearGradient id="floorfade" x1="0" y1="{HZ}" x2="0" y2="{H}" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset=".45" stop-color="#fff" stop-opacity=".9"/><stop offset="1" stop-color="#fff" stop-opacity=".25"/></linearGradient>
<mask id="floor"><rect y="{HZ}" width="{W}" height="{H - HZ}" fill="url(#floorfade)"/></mask>
<linearGradient id="refl" x1="0" y1="0" x2="0" y2="1"><stop offset=".45" stop-color="#fff" stop-opacity="0"/><stop offset="1" stop-color="#fff" stop-opacity=".8"/></linearGradient>
<mask id="reflect" maskContentUnits="objectBoundingBox"><rect width="1" height="1" fill="url(#refl)"/></mask>
<linearGradient id="hzline" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{GRID}" stop-opacity="0"/><stop offset=".5" stop-color="{LIME}"/><stop offset="1" stop-color="{GRID}" stop-opacity="0"/></linearGradient>
<linearGradient id="vinegrad" x1="436" y1="0" x2="844" y2="0" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="{KICK}"/><stop offset=".5" stop-color="{LIME}"/><stop offset="1" stop-color="{TEAL}"/></linearGradient>
<filter id="blur6" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="6"/></filter>
<filter id="blur24" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="24"/></filter>
{card(W, H, (.5, .62))}'''

    body = f'''<g clip-path="url(#cardclip)">
<ellipse cx="640" cy="{HZ}" rx="520" ry="70" fill="{GRID}" opacity=".08" filter="url(#blur24)"/>
<g mask="url(#floor)" fill="none" stroke-width="1.2"><g stroke="{GRID}" stroke-opacity=".28">{verticals}</g><g stroke-opacity=".45">{rows}</g></g>
<path class="horizon" d="M60 {HZ}H{W - 60}" stroke="url(#hzline)" stroke-width="1.5"/>
{''.join(flies)}
</g>
<g transform="translate(580 40)">{icon('streamorchard', 'h-so', 0, 0, 120)}
<circle class="beat" cx="60" cy="60" r="20" fill="none" stroke="{LIME}" stroke-width="2"/></g>
{text([('stream', 400, MID), ('orchard', 800, TEXT)], 640, 252, 84, anchor='middle', track=-.03)}
{text('Desktop apps for people who live on live streams', 640, 298, 24, 400, DIM, 'middle')}
<path d="{vine}" fill="none" stroke="url(#vinegrad)" stroke-width="6" opacity=".25" filter="url(#blur6)"/>
<path id="vine" d="{vine}" fill="none" stroke="url(#vinegrad)" stroke-width="2.5" stroke-linecap="round" opacity=".85"/>
{pulses}
{''.join(icons)}
{''.join(labels)}'''
    return svg(W, H, 'StreamOrchard: desktop apps for people who live on live streams', style, defs, body)


# ---------------------------------------------------------------- Stream Multiview

def multiview():
    W, H = 1280, 440
    X0, Y0 = 664, 104  # the window's content area, 536 x 268
    hold, move = 2.6, .8
    focus_a = {'s1': (0, 0, 364, 268), 's2': (372, 0, 164, 90), 's3': (372, 98, 164, 90), 'c': (372, 196, 164, 72)}
    tile = {'s1': (0, 0, 264, 130), 's2': (272, 0, 264, 130), 's3': (0, 138, 264, 130), 'c': (272, 138, 264, 130)}
    focus_b = {**focus_a, 's1': focus_a['s2'], 's2': focus_a['s1']}
    columns = {'s1': (0, 0, 172, 168), 's2': (182, 0, 172, 168), 's3': (364, 0, 172, 168), 'c': (0, 176, 536, 92)}
    states = [focus_a, tile, focus_b, columns]
    names = ['Focus view', 'Tile', 'Focus view', 'Columns']
    main = ['s1', 's1', 's2', 's2']
    n, T = len(states), len(states) * (hold + move)

    times = []
    for i in range(n):
        times += [i * (hold + move), i * (hold + move) + hold]
    times.append(T)
    key_times = ';'.join(f'{t / T:.4f}' for t in times)
    splines = ';'.join(['0 0 1 1', '.65 0 .35 1'] * n)

    def anim(attr, vals):
        vals = [v for v in vals for _ in (0, 1)] + [vals[0]]
        return (f'<animate attributeName="{attr}" dur="{T}s" repeatCount="indefinite" calcMode="spline" '
                f'keyTimes="{key_times}" keySplines="{splines}" values="{";".join(num(v) for v in vals)}"/>')

    def geom(key, grow=0):
        boxes = [s[key] for s in states]
        return ''.join(anim(a, [b[i] + (X0, Y0, 0, 0)[i] - (grow if i < 2 else -2 * grow) for b in boxes])
                       for i, a in enumerate(('x', 'y', 'width', 'height')))

    streams = [('s1', 'PixelPear', KICK, ('#ff8a3d', '#9b5cff')), ('s2', 'LunaPlays', TWITCH, ('#3da9ff', '#5b3dff')),
               ('s3', 'orchard fm', YOUTUBE, ('#ff3d7f', '#ffb13d'))]
    tiles = []
    for key, label, dot, (a, b) in streams:
        tiles.append(f'''<svg x="0" y="0" width="1" height="1">{geom(key)}
<clipPath id="clip-{key}"><rect width="100%" height="100%" rx="9"/></clipPath>
<radialGradient id="ga-{key}" cx=".32" cy=".55" r=".55"><stop offset="0" stop-color="{a}" stop-opacity=".9"/><stop offset="1" stop-color="{a}" stop-opacity="0"/></radialGradient>
<radialGradient id="gb-{key}" cx=".72" cy=".78" r=".6"><stop offset="0" stop-color="{b}" stop-opacity=".85"/><stop offset="1" stop-color="{b}" stop-opacity="0"/></radialGradient>
<g clip-path="url(#clip-{key})"><rect width="100%" height="100%" fill="#120f1c"/>
<rect width="100%" height="100%" fill="url(#gb-{key})" class="drift"/><rect width="100%" height="100%" fill="url(#ga-{key})"/>
<rect width="100%" height="24" fill="#070a08" fill-opacity=".72"/>
<circle cx="13" cy="12" r="4" fill="{dot}"/>{text(label, 23, 16, 11, 600, TEXT)}
<rect x="8" y="32" width="34" height="16" rx="4" fill="#e5484d"/>{text('LIVE', 25, 43.5, 9, 800, '#fff', 'middle', track=.06)}
<svg x="100%" y="0" overflow="visible"><g transform="translate(-26 7)" fill="{LIME}">
<rect class="eq" x="0" width="3" height="10" rx="1.5"/><rect class="eq" x="5" width="3" height="10" rx="1.5" style="animation-delay:-.3s"/><rect class="eq" x="10" width="3" height="10" rx="1.5" style="animation-delay:-.6s"/></g></svg>
</g></svg>''')

    chat_colors = [KICK, '#ff8a3d', '#ff5fa2', '#ffd23d', '#3da9ff', TWITCH, KICK, '#ff8a3d', '#3da9ff', '#ff5fa2']
    rnd = random.Random(3)
    chat_lines = ''.join(f'<rect x="10" y="{num(34 + i * 13)}" width="{rnd.randint(18, 34)}" height="5" rx="2.5" fill="{c}"/>'
                         f'<rect x="{50}" y="{num(34 + i * 13)}" width="{rnd.randint(40, 200)}" height="5" rx="2.5" fill="#fff" fill-opacity=".14"/>'
                         for i, c in enumerate(chat_colors * 2))
    tiles.append(f'''<svg x="0" y="0" width="1" height="1">{geom('c')}
<clipPath id="clip-c"><rect width="100%" height="100%" rx="9"/></clipPath>
<g clip-path="url(#clip-c)"><rect width="100%" height="100%" fill="#0b100d"/>
<g class="chat">{chat_lines}</g>
<rect width="100%" height="24" fill="#0b100d"/><circle cx="13" cy="12" r="4" fill="{KICK}"/>{text('Chat', 23, 16, 11, 600, TEXT)}</g>
<rect width="100%" height="100%" rx="9" fill="none" stroke="#fff" stroke-opacity=".07"/></svg>''')

    focus = f'''<rect x="0" y="0" width="1" height="1" rx="10" fill="none" stroke="{KICK}" stroke-width="2">{''.join(
        anim(a, [states[i][main[i]][j] + (X0, Y0, 0, 0)[j] + (-1, -1, 2, 2)[j] for i in range(n)])
        for j, a in enumerate(('x', 'y', 'width', 'height')))}</rect>'''
    focus_glow = focus.replace('fill="none"', 'fill="none" filter="url(#blur8)" opacity=".7"', 1).replace('stroke-width="2"', 'stroke-width="5"', 1)

    labels = []
    switch = [0] + [i * (hold + move) - move for i in range(1, n)] + [T - move]  # when each layout is picked
    for i, name in enumerate(names):
        vals = [1 if j % n == i else 0 for j in range(n + 1)]
        labels.append(f'<g opacity="0">{text(name, 1094, 77, 12, 600, TEXT, "middle")}<animate attributeName="opacity" dur="{T}s" '
                      f'repeatCount="indefinite" calcMode="discrete" keyTimes="{";".join(f"{t / T:.4f}" for t in switch)}" values="{";".join(map(str, vals))}"/></g>')

    window = f'''<rect x="640" y="44" width="584" height="352" rx="18" fill="#000" opacity=".5" filter="url(#blur24)"/>
<rect x="640" y="44" width="584" height="352" rx="18" fill="#0d1210"/>
<rect x="640.75" y="44.75" width="582.5" height="350.5" rx="17.25" fill="none" stroke="{GRID}" stroke-opacity=".16" stroke-width="1.5"/>
<circle cx="666" cy="72" r="6" fill="#ff5f57"/><circle cx="686" cy="72" r="6" fill="#febc2e"/><circle cx="706" cy="72" r="6" fill="#28c840"/>
<rect x="728" y="58" width="196" height="28" rx="8" fill="#000" fill-opacity=".45" stroke="#fff" stroke-opacity=".06"/>
{text('kick.com/pixelpear', 742, 77, 12, 400, DIM)}
<rect x="932" y="58" width="56" height="28" rx="8" fill="{KICK}"/>{text('Add', 960, 77, 12, 700, '#0a1406', 'middle')}
<rect x="1040" y="58" width="108" height="28" rx="8" fill="#fff" fill-opacity=".05" stroke="#fff" stroke-opacity=".1"/>
{''.join(labels)}
<rect x="1156" y="58" width="44" height="28" rx="8" fill="#fff" fill-opacity=".05" stroke="#fff" stroke-opacity=".1"/>
<g fill="{MID}"><rect x="1167" y="65" width="9" height="14" rx="2"/><rect x="1179" y="65" width="10" height="6" rx="2"/><rect x="1179" y="73" width="10" height="6" rx="2"/></g>'''

    style = f'''
.eq {{ transform-box: fill-box; transform-origin: bottom; animation: eq 1.1s ease-in-out infinite alternate; }}
@keyframes eq {{ from {{ transform: scaleY(.3); }} to {{ transform: scaleY(1); }} }}
.chat {{ animation: chat 13s linear infinite; }}
@keyframes chat {{ from {{ transform: translateY(0); }} to {{ transform: translateY(-130px); }} }}
.drift {{ animation: drift 7s ease-in-out infinite alternate; }}
@keyframes drift {{ from {{ opacity: .55; }} to {{ opacity: 1; }} }}'''
    defs = f'''<filter id="blur8" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="6"/></filter>
<filter id="blur24" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="22"/></filter>
{card(W, H, (.72, .2))}'''
    words = blurb(72, 'WATCH EVERYTHING AT ONCE', ('Stream', 'Multiview'),
                  wrap('Kick, Twitch and YouTube streams and their chats side by side, in any layout you like, with live alerts and a game focus mode.', 20, 480),
                  [('Kick', KICK), ('Twitch', TWITCH), ('YouTube', YOUTUBE)], multiview_icon('i-mv', 72, 56, 52))
    body = f'{words}\n{window}\n{"".join(tiles)}\n{focus_glow}{focus}'
    return svg(W, H, 'Stream Multiview: Kick, Twitch and YouTube streams and chats side by side, in any layout', style, defs, body)


# ---------------------------------------------------------------- Pear Drops

def pear_drops():
    W, H, T = 1280, 440, 12
    CX, CY, R = 512, 214, 70
    circ = 2 * 3.14159265 * R
    rewards = [('Pear Badge', 30, ('#ff5fa2', '#9b5cff')), ('Hype Rocket Emote', 60, ('#ffb13d', '#ff6a3d')),
               ('Neon Crown', 120, ('#3dffd0', '#14a6c7'))]
    full = .75  # all 120 minutes watched at 75% of the loop

    style = [f'''
.dyn {{ animation: dyn {T}s linear infinite; }}
@keyframes dyn {{ 0% {{ opacity: 0; }} 2%, 93% {{ opacity: 1; }} 98%, 100% {{ opacity: 0; }} }}
.bar {{ transform-box: fill-box; transform-origin: left center; }}
.ring {{ stroke-dasharray: {circ:.1f}; animation: ring {T}s linear infinite; }}
@keyframes ring {{ 0% {{ stroke-dashoffset: {circ:.1f}; }} {full * 100}%, 100% {{ stroke-dashoffset: 0; }} }}
.level {{ animation: level {T}s linear infinite; }}
@keyframes level {{ 0% {{ transform: translateY(0); }} {full * 100}%, 100% {{ transform: translateY(-104px); }} }}
.wave {{ animation: wave 1.6s linear infinite; }}
@keyframes wave {{ from {{ transform: translateX(0); }} to {{ transform: translateX(-40px); }} }}
.done {{ animation: done {T}s ease-out infinite; }}
@keyframes done {{ 0%, {full * 100 - .5}% {{ opacity: 0; }} {full * 100 + 3}%, 93% {{ opacity: 1; }} 98%, 100% {{ opacity: 0; }} }}
.todo {{ animation: todo {T}s ease-out infinite; }}
@keyframes todo {{ 0%, {full * 100 - .5}% {{ opacity: 1; }} {full * 100 + 3}%, 95% {{ opacity: 0; }} 99%, 100% {{ opacity: 1; }} }}
.pop {{ transform-box: fill-box; transform-origin: center; }}''']

    rows = []
    for i, (name, need, (a, b)) in enumerate(rewards):
        y = 136 + i * 66
        at = full * need / 120 * 100
        style.append(f'''
#bar{i} {{ animation: bar{i} {T}s linear infinite; }}
@keyframes bar{i} {{ 0% {{ transform: scaleX(0); }} {at:.2f}%, 100% {{ transform: scaleX(1); }} }}
#got{i} {{ animation: got{i} {T}s ease-out infinite; }}
@keyframes got{i} {{ 0%, {at - .3:.2f}% {{ opacity: 0; }} {at + 1.5:.2f}%, 93% {{ opacity: 1; }} 97%, 100% {{ opacity: 0; }} }}
#need{i} {{ animation: need{i} {T}s ease-out infinite; }}
@keyframes need{i} {{ 0%, {at - .3:.2f}% {{ opacity: 1; }} {at + 1.5:.2f}%, 95% {{ opacity: 0; }} 99%, 100% {{ opacity: 1; }} }}
#burst{i} {{ animation: burst{i} {T}s ease-out infinite; }}
@keyframes burst{i} {{ 0%, {at - .2:.2f}% {{ opacity: 0; transform: scale(.5); }} {at:.2f}% {{ opacity: 1; transform: scale(.8); }} {at + 6:.2f}%, 100% {{ opacity: 0; transform: scale(2.6); }} }}''')
        rows.append(f'''<linearGradient id="rw{i}" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{a}"/><stop offset="1" stop-color="{b}"/></linearGradient>
<rect x="92" y="{y}" width="300" height="54" rx="12" fill="#fff" fill-opacity=".03" stroke="#fff" stroke-opacity=".07"/>
<rect id="got{i}" x="92" y="{y}" width="300" height="54" rx="12" fill="{KICK}" fill-opacity=".05" stroke="{KICK}" stroke-opacity=".55"/>
<circle id="burst{i}" class="pop" cx="122" cy="{y + 27}" r="16" fill="none" stroke="{LIME}" stroke-width="2"/>
<rect x="106" y="{y + 11}" width="32" height="32" rx="9" fill="url(#rw{i})"/>
{text(name, 152, y + 23, 14, 600, TEXT)}
<rect x="152" y="{y + 33}" width="160" height="5" rx="2.5" fill="#fff" fill-opacity=".09"/>
<rect id="bar{i}" class="bar" x="152" y="{y + 33}" width="160" height="5" rx="2.5" fill="url(#fruit)"/>
<g id="need{i}">{text(f'{need} min', 378, y + 32, 12, 600, DIM, 'end')}</g>
<g id="got{i}t" style="animation: got{i} {T}s ease-out infinite">{text('Claimed', 378, y + 32, 12, 700, KICK, 'end')}</g>''')

    s = 96 / 722  # the drop is 722 units tall in the Pear Drops icon
    drop_t = f'translate({CX} {CY + 2}) scale({s:.4f}) translate(-512 -537)'
    wave = 'M-40 0' + ''.join(f'q10 -5 20 0t20 0' for _ in range(8)) + 'V140H-40Z'
    dial = f'''<circle cx="{CX}" cy="{CY}" r="{R + 22}" fill="{KICK}" fill-opacity=".3" opacity="0" filter="url(#blur24)" class="done"/>
<circle cx="{CX}" cy="{CY}" r="{R}" fill="none" stroke="#fff" stroke-opacity=".07" stroke-width="10"/>
<circle class="ring dyn" cx="{CX}" cy="{CY}" r="{R}" fill="none" stroke="url(#ringgrad)" stroke-width="10" stroke-linecap="round" transform="rotate(-90 {CX} {CY})"/>
<clipPath id="dropclip"><path d="{DROP}" transform="{drop_t}"/></clipPath>
<path d="{DROP}" transform="{drop_t}" fill="#0f1a13"/>
<g clip-path="url(#dropclip)"><g transform="translate({CX - 40} {CY + 52})"><g class="level"><g class="dyn"><g class="wave">
<path d="{wave}" fill="url(#liquid)"/></g></g></g></g></g>
<g transform="{drop_t}"><path d="{DROP}" fill="none" stroke="{LIME}" stroke-opacity=".45" stroke-width="10"/>
<g transform="translate(512 646) scale(.5) translate(-512 -520)" fill="#0a1406" fill-opacity=".85"><path d="{PEAR}"/><path d="{PEAR_LEAF}"/>
<path d="{PEAR_STEM}" stroke="#0a1406" stroke-opacity=".85" stroke-width="46" stroke-linecap="round" fill="none"/></g></g>
<g class="todo">{text("Kick's own player, muted", CX, CY + 108, 12, 500, DIM, 'middle')}</g>
<g class="done">{text('All rewards claimed', CX, CY + 108, 12, 700, KICK, 'middle')}</g>'''

    dash = f'''<rect x="64" y="44" width="560" height="352" rx="18" fill="#000" opacity=".5" filter="url(#blur24)"/>
<rect x="64" y="44" width="560" height="352" rx="18" fill="#0d1210"/>
<rect x="64.75" y="44.75" width="558.5" height="350.5" rx="17.25" fill="none" stroke="{GRID}" stroke-opacity=".16" stroke-width="1.5"/>
{text('NOW FARMING', 92, 86, 11, 700, KICK, track=.14)}
{text([('Launch Week', 700, TEXT), (' · Neon Rush', 500, DIM)], 92, 114, 20)}
<rect x="476" y="66" width="120" height="28" rx="14" fill="{KICK}" fill-opacity=".08" stroke="{KICK}" stroke-opacity=".35"/>
<circle cx="494" cy="80" r="4" fill="{KICK}"><animate attributeName="opacity" values="1;.3;1" dur="1.6s" repeatCount="indefinite"/></circle>
{text('Watching', 504, 84.5, 12, 600, TEXT)}
{''.join(rows)}
{dial}
<path d="M92 352H596" stroke="#fff" stroke-opacity=".06"/>
<circle cx="100" cy="373" r="4" fill="{KICK}"/>{text([('PixelPear', 600, TEXT), ('  ·  1,240 watching', 400, DIM)], 112, 377.5, 12)}
{text('Moves on to the next drop when it’s done', 596, 377.5, 12, 400, DIM, 'end')}'''

    defs = f'''<linearGradient id="ringgrad" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{LIME}"/><stop offset="1" stop-color="{KICK}"/></linearGradient>
<linearGradient id="liquid" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#b6ff8f"/><stop offset=".35" stop-color="{KICK}"/><stop offset="1" stop-color="#1fae06"/></linearGradient>
<filter id="blur24" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="22"/></filter>
{card(W, H, (.28, .2))}'''
    words = blurb(688, 'COLLECT DROPS WHILE YOU WATCH', ('Pear', 'Drops'),
                  ['Collects your Kick emote and badge drops', 'with Kick’s own player, while you get on', 'with something else.'],
                  [('Auto-claim', KICK), ('Stall recovery', AMBER), ('History', VIOLET)], icon('pear-drops', 'i-pd', 688, 56, 52, '100 100 824 824'))
    body = f'{dash}\n{words}'
    return svg(W, H, "Pear Drops: collects your Kick emote and badge drops with Kick's own player", ''.join(style), defs, body)


# ---------------------------------------------------------------- Grapevine

def grapevine():
    W, H, T = 1280, 440, 12
    A, B, CY, S = 726, 1138, 152, 92  # Pear Drops and Stream Multiview icon centres, their size
    vine = f'M{A + 50} {CY}C{A + 96} {CY - 36} {A + 150} {CY + 36} 932 {CY}C{B - 150} {CY - 36} {B - 96} {CY + 36} {B - 50} {CY}'

    def packet(label, start, end, reverse=False, small=False):
        kt = f'0;{start};{end};1'
        kp = '1;1;0;0' if reverse else '0;0;1;1'
        chip = ''
        if label:
            w = textw(label, 11, 500, 'mono') + 20
            chip = (f'<rect x="{num(-w / 2)}" y="-38" width="{num(w)}" height="22" rx="11" fill="#0b120e" stroke="{LIME}" stroke-opacity=".45"/>'
                    + text(label, 0, -23, 11, 500, LIME, 'middle', 'mono'))
        r = 3 if small else 5
        return (f'<g opacity="0"><circle r="{r * 3}" fill="url(#spark)"/><circle r="{r}" fill="{TEAL if reverse else LIME}"/>{chip}'
                f'<animateMotion dur="{T}s" repeatCount="indefinite" keyPoints="{kp}" keyTimes="{kt}" calcMode="linear"><mpath href="#vine"/></animateMotion>'
                f'<animate attributeName="opacity" dur="{T}s" repeatCount="indefinite" values="0;0;1;1;0;0" keyTimes="0;{start - .005};{start};{end};{end + .01};1"/></g>')

    # the story: Pear Drops starts farming, tells Multiview, Multiview signs its Kick players out and says so
    packets = (packet('drops.farming.changed', .06, .22) + packet('players.changed', .32, .48, reverse=True)
               + packet('', .6, .66, small=True) + packet('', .66, .72, reverse=True, small=True))
    log = [('out', 'event', 'drops.farming.changed', 'to Stream Multiview · 1290 B', .22),
           ('in', 'event', 'players.changed', 'from Stream Multiview · 214 B', .48),
           ('out', 'request', 'link.ping', 'answered in 2 ms', .72)]
    style = [f'''
.arrive {{ transform-box: fill-box; transform-origin: center; }}
.signedin {{ animation: signedin {T}s ease infinite; }}
@keyframes signedin {{ 0%, 24% {{ opacity: 1; }} 26%, 95% {{ opacity: 0; }} 99%, 100% {{ opacity: 1; }} }}
.signedout {{ animation: signedout {T}s ease infinite; }}
@keyframes signedout {{ 0%, 24% {{ opacity: 0; }} 26%, 95% {{ opacity: 1; }} 99%, 100% {{ opacity: 0; }} }}
.leaf {{ transform-box: fill-box; transform-origin: 0 100%; animation: leaf 5s ease-in-out infinite alternate; }}
@keyframes leaf {{ from {{ transform: rotate(-6deg); }} to {{ transform: rotate(6deg); }} }}''']
    for i, (_, _, _, _, at) in enumerate(log):
        style.append(f'''
#log{i} {{ animation: log{i} {T}s ease-out infinite; }}
@keyframes log{i} {{ 0%, {at * 100:.1f}% {{ opacity: 0; transform: translateX(-8px); }} {at * 100 + 2:.1f}%, 94% {{ opacity: 1; transform: translateX(0); }} 98%, 100% {{ opacity: 0; }} }}''')
    for name, at in (('a', .72), ('b', .22), ('a2', .48)):
        style.append(f'''
#ping-{name} {{ animation: ping-{name} {T}s ease-out infinite; }}
@keyframes ping-{name} {{ 0%, {at * 100 - .3:.1f}% {{ opacity: 0; transform: scale(.9); }} {at * 100:.1f}% {{ opacity: .9; transform: scale(1); }} {at * 100 + 7:.1f}%, 100% {{ opacity: 0; transform: scale(1.5); }} }}''')

    def ring(id_, cx):
        return f'<rect id="{id_}" class="arrive" x="{cx - S / 2}" y="{CY - S / 2}" width="{S}" height="{S}" rx="{S * .22}" fill="none" stroke="{LIME}" stroke-width="2"/>'

    leaves = ''.join(f'<g transform="translate({x} {y}) rotate({r})"><path class="leaf" style="animation-delay:-{d}s" d="M0 0C4 -12 16 -16 26 -12C22 -2 10 2 0 0Z" fill="url(#leafgrad)" opacity=".8"/></g>'
                     for x, y, r, d in [(812, 140, -30, 0), (862, 166, 160, 1.5), (1004, 140, -20, 3), (1056, 166, 150, 2)])

    lock = f'<g transform="translate(842 70)" fill="none" stroke="{LIME}" stroke-width="1.8"><rect x="0" y="6" width="12" height="9" rx="2" fill="{LIME}" fill-opacity=".15"/><path d="M2.5 6V4a3.5 3.5 0 0 1 7 0v2"/></g>'

    log_rows = []
    for i, (d, kind, method, meta, _) in enumerate(log):
        y = 330 + i * 22
        arrow = 'M0 0H10M6 -4L10 0L6 4' if d == 'out' else 'M10 0H0M4 -4L0 0L4 4'
        log_rows.append(f'''<g id="log{i}"><path transform="translate(700 {y - 4})" d="{arrow}" fill="none" stroke="{LIME if d == 'out' else TEAL}" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
{text(kind, 722, y, 12, 400, DIM, family='mono')}{text(method, 792, y, 12, 600, TEXT, family='mono')}
{text(meta, 1176, y, 12, 400, DIM, 'end', 'mono')}</g>''')

    art = f'''<rect x="832" y="60" width="200" height="28" rx="14" fill="#fff" fill-opacity=".03" stroke="#fff" stroke-opacity=".09"/>
{lock}{text('Paired · this computer only', 862, 79, 12, 500, MID)}
<path d="{vine}" fill="none" stroke="url(#vinegrad)" stroke-width="8" opacity=".25" filter="url(#blur6)"/>
<path id="vine" d="{vine}" fill="none" stroke="url(#vinegrad)" stroke-width="3" stroke-linecap="round"/>
{leaves}
<circle cx="932" cy="{CY}" r="40" fill="{GRID}" opacity=".18" filter="url(#blur6)"/>
{icon('grapevine', 'g-gv', 932 - 30, CY - 30, 60)}
{packets}
{icon('pear-drops', 'g-pd', A - S / 2, CY - S / 2, S, '100 100 824 824')}{ring('ping-a', A)}{ring('ping-a2', A)}
{multiview_icon('g-mv', B - S / 2, CY - S / 2, S)}{ring('ping-b', B)}
{text('Pear Drops', A, 232, 16, 700, TEXT, 'middle')}
<g><circle cx="{A - 62}" cy="252" r="4" fill="{KICK}"/>{text('Farming PixelPear', A - 52, 256.5, 13, 500, MID)}</g>
{text('Stream Multiview', B, 232, 16, 700, TEXT, 'middle')}
<g class="signedin"><circle cx="{B - 76}" cy="252" r="4" fill="{AMBER}"/>{text('Kick players signed in', B - 66, 256.5, 13, 500, MID)}</g>
<g class="signedout"><circle cx="{B - 80}" cy="252" r="4" fill="{KICK}"/>{text('Kick players signed out', B - 70, 256.5, 13, 500, MID)}</g>
<rect x="680" y="298" width="516" height="102" rx="14" fill="#000" fill-opacity=".35" stroke="#fff" stroke-opacity=".07"/>
{text('ACTIVITY', 700, 314, 10, 700, DIM, track=.16)}
<g transform="translate(0 8)">{''.join(log_rows)}</g>'''

    defs = f'''<linearGradient id="vinegrad" x1="{A}" y1="0" x2="{B}" y2="0" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="{KICK}"/><stop offset=".5" stop-color="{LIME}"/><stop offset="1" stop-color="{TEAL}"/></linearGradient>
<linearGradient id="leafgrad" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{LIME}"/><stop offset="1" stop-color="#2fd36b"/></linearGradient>
<radialGradient id="spark"><stop offset="0" stop-color="{LIME}" stop-opacity=".6"/><stop offset="1" stop-color="{LIME}" stop-opacity="0"/></radialGradient>
<filter id="blur6" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="6"/></filter>
{card(W, H, (.72, .3))}'''
    words = blurb(72, 'THE VINE BETWEEN THEM', [('grape', 400, MID), ('vine', 800, TEXT)],
                  ['Lets your desktop apps find each other and', 'talk, privately, right on your computer.', 'No account, no server, nothing online.'],
                  [('Pairs safely', LIME), ('Versioned', TEAL), ('Reconnects', VIOLET)], icon('grapevine', 'i-gv', 72, 56, 52))
    body = f'{words}\n{art}'
    return svg(W, H, 'Grapevine: lets desktop apps on the same computer find each other and talk, privately', ''.join(style), defs, body)


if __name__ == '__main__':
    OUT.mkdir(exist_ok=True)
    for name, build in [('hero', hero), ('stream-multiview', multiview), ('pear-drops', pear_drops), ('grapevine', grapevine)]:
        out = OUT / f'{name}.svg'
        out.write_text(build())
        print(f'{out.relative_to(ROOT)}  {out.stat().st_size // 1024} KB')
