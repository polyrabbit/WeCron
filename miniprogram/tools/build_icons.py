#!/usr/bin/env python3
"""Generates the PNG icons in ../images, requires rsvg-convert. Icon paths are from Feather Icons:

The MIT License (MIT)

Copyright (c) 2013-2023 Cole Bemis

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
import os
import subprocess
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'images')

POSITIVE = '#387ef5'
GREY = '#aaaaaa'
DARK = '#444444'

ICONS = {
    'clock': '<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>',
    'bell': '<path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/>',
    'repeat': '<polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/>'
              '<path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/>',
    'users': '<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/>'
             '<path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
    'note': '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>'
            '<polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/>'
            '<line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/>',
    'trash': '<polyline points="3 6 5 6 21 6"/>'
             '<path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>'
             '<line x1="10" y1="11" x2="10" y2="17"/><line x1="14" y1="11" x2="14" y2="17"/>',
    'quit': '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/>'
            '<line x1="21" y1="12" x2="9" y2="12"/>',
    'share': '<circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/>'
             '<line x1="8.59" y1="13.51" x2="15.42" y2="17.49"/><line x1="15.41" y1="6.51" x2="8.59" y2="10.49"/>',
    'check': '<polyline points="20 6 9 17 4 12"/>',
    'chevron': '<polyline points="9 18 15 12 9 6"/>',
}

GEAR = ('M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 '
        '1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06'
        'a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 '
        '2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 '
        '0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 '
        '1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 '
        '0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z')


def stroke_svg(body, color, width=1.8):
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="-1 -1 26 26" fill="none" stroke="%s" '
            'stroke-width="%s" stroke-linecap="round" stroke-linejoin="round">%s</svg>' % (color, width, body))


# Tab bar: outline when inactive, solid when active
TABS = {
    'tab-remind': stroke_svg(ICONS['clock'], '#c3d8fc'),
    'tab-remind-active': '<svg xmlns="http://www.w3.org/2000/svg" viewBox="-1 -1 26 26">'
                         '<circle cx="12" cy="12" r="11" fill="#fff"/>'
                         '<polyline points="12 6 12 12 16 14" fill="none" stroke="%s" stroke-width="2.2" '
                         'stroke-linecap="round" stroke-linejoin="round"/></svg>' % POSITIVE,
    'tab-settings': stroke_svg('<circle cx="12" cy="12" r="3"/><path d="%s"/>' % GEAR, '#c3d8fc'),
    'tab-settings-active': '<svg xmlns="http://www.w3.org/2000/svg" viewBox="-1 -1 26 26">'
                           '<path d="%s" fill="#fff" stroke="#fff" stroke-width="1.8" stroke-linejoin="round"/>'
                           '<circle cx="12" cy="12" r="3.2" fill="%s"/></svg>' % (GEAR, POSITIVE),
}

def render(name, svg, size):
    with tempfile.NamedTemporaryFile('w', suffix='.svg', delete=False) as f:
        f.write(svg)
    try:
        subprocess.check_call(['rsvg-convert', '-w', str(size), '-h', str(size), '-o',
                               os.path.join(OUT, name + '.png'), f.name])
    finally:
        os.unlink(f.name)


def main():
    os.makedirs(OUT, exist_ok=True)
    for name, svg in TABS.items():
        render(name, svg, 81)
    variants = {'grey': GREY, 'dark': DARK, 'white': '#ffffff'}
    needed = {
        'clock': ['grey'], 'bell': ['grey'], 'repeat': ['grey'], 'users': ['grey'], 'note': ['grey'],
        'chevron': ['grey', 'white'], 'trash': ['dark'], 'quit': ['dark'],
        'share': ['dark'], 'check': ['white'],
    }
    for name, colors in needed.items():
        for color in colors:
            render('%s-%s' % (name, color), stroke_svg(ICONS[name], variants[color]), 72)
    print('Icons written to', OUT)


if __name__ == '__main__':
    main()
