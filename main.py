#!/usr/bin/env python3
"""World in One Day - 22 November 2026.

A deterministic, standard-library-only program that draws a one-page
newspaper summing up the world news of Sunday 22 November 2026 and
writes it to /output/entry.png (or $MAKEFUN_OUTPUT_DIR/entry.png).

The picture is drawn entirely by this code: a pixel canvas, a built-in
5x7 bitmap font, flat-colour illustrations and a hand-rolled PNG
encoder (zlib + struct). No network, no randomness, no clock: two
runs always produce byte-identical output.

The day's stories (all reported on 22 November 2026):
  * COP31, Antalya: the summit ran into double overtime and the
    eleventh-hour Sunday draft deal still did not mention fossil
    fuels; the EU and island states pushed back. The draft keeps a
    goal of electricity reaching 35% of final energy use by 2035.
  * Gulf escalation: two tankers were hit near the Strait of Hormuz,
    Bahrain said Iran set fire to a civilian industrial site, and the
    Saudi-led coalition intercepted three Houthi ballistic missiles
    fired at Riyadh; the coalition also struck Hodeidah port.
  * France: protesters rallied for a sixth weekend over living
    costs and public services.
  * Florida: the St. Johns River held a record 18.8 ft near Cocoa,
    above the 1953 mark, with airboat rescues and the crest rolling
    north for days.
  * India: toxic alcohol killed at least 11 people in Manipur state,
    with more than 180 in hospital.
  * Peru: a magnitude 6.7 earthquake shook the central Andes near
    Junin and was felt in Lima; first reports said minor damage and
    no deaths.
  * Sport: Verstappen won the Las Vegas Grand Prix; Mao Shimada won
    the Finlandia Trophy to book a Grand Prix Final spot.
"""

import os
import struct
import zlib

W, H = 1024, 1024

# ---------------------------------------------------------------- PNG out

def write_png(path, width, height, rgb):
    """Write an RGB bytearray as a PNG file (filter 0 rows)."""
    raw = bytearray()
    stride = width * 3
    for y in range(height):
        raw.append(0)
        raw += rgb[y * stride:(y + 1) * stride]

    def chunk(tag, data):
        out = struct.pack(">I", len(data)) + tag + data
        out += struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        return out

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += chunk(b"IEND", b"")
    with open(path, "wb") as fh:
        fh.write(png)

# ---------------------------------------------------------------- canvas

class Canvas:
    def __init__(self, w, h, bg):
        self.w, self.h = w, h
        self.px = bytearray(bg * (w * h))

    def set(self, x, y, col):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i:i + 3] = bytes(col)

    def rect(self, x, y, w, h, col):
        for yy in range(y, y + h):
            if 0 <= yy < self.h:
                base = (yy * self.w) * 3
                for xx in range(max(x, 0), min(x + w, self.w)):
                    i = base + xx * 3
                    self.px[i:i + 3] = bytes(col)

    def frame(self, x, y, w, h, t, col):
        self.rect(x, y, w, t, col)
        self.rect(x, y + h - t, w, t, col)
        self.rect(x, y, t, h, col)
        self.rect(x + w - t, y, t, h, col)

    def circle(self, cx, cy, r, col):
        for yy in range(cy - r, cy + r + 1):
            for xx in range(cx - r, cx + r + 1):
                if (xx - cx) ** 2 + (yy - cy) ** 2 <= r * r:
                    self.set(xx, yy, col)

    def ring(self, cx, cy, r, t, col):
        for yy in range(cy - r - t, cy + r + t + 1):
            for xx in range(cx - r - t, cx + r + t + 1):
                d = (xx - cx) ** 2 + (yy - cy) ** 2
                if r * r <= d <= (r + t) * (r + t):
                    self.set(xx, yy, col)

    def line(self, x0, y0, x1, y1, col, t=1):
        dx, dy = abs(x1 - x0), abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err, x, y = dx - dy, x0, y0
        while True:
            for ox in range(t):
                for oy in range(t):
                    self.set(x + ox, y + oy, col)
            if x == x1 and y == y1:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x += sx
            if e2 < dx:
                err += dx
                y += sy

    def tri(self, x0, y0, x1, y1, x2, y2, col):
        minx, maxx = min(x0, x1, x2), max(x0, x1, x2)
        miny, maxy = min(y0, y1, y2), max(y0, y1, y2)

        def edge(ax, ay, bx, by, px_, py_):
            return (px_ - ax) * (by - ay) - (py_ - ay) * (bx - ax)

        for yy in range(miny, maxy + 1):
            for xx in range(minx, maxx + 1):
                w0 = edge(x1, y1, x2, y2, xx, yy)
                w1 = edge(x2, y2, x0, y0, xx, yy)
                w2 = edge(x0, y0, x1, y1, xx, yy)
                if (w0 >= 0 and w1 >= 0 and w2 >= 0) or \
                   (w0 <= 0 and w1 <= 0 and w2 <= 0):
                    self.set(xx, yy, col)

# ---------------------------------------------------------------- font
# 5x7 bitmap font, one tuple of 7 row-strings per character ('#' = ink).

FONT = {
    "A": (".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "B": ("####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."),
    "C": (".####", "#....", "#....", "#....", "#....", "#....", ".####"),
    "D": ("####.", "#...#", "#...#", "#...#", "#...#", "#...#", "####."),
    "E": ("#####", "#....", "#....", "####.", "#....", "#....", "#####"),
    "F": ("#####", "#....", "#....", "####.", "#....", "#....", "#...."),
    "G": (".####", "#....", "#....", "#.###", "#...#", "#...#", ".###."),
    "H": ("#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "I": ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "#####"),
    "J": ("..###", "...#.", "...#.", "...#.", "...#.", "#..#.", ".##.."),
    "K": ("#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#"),
    "L": ("#....", "#....", "#....", "#....", "#....", "#....", "#####"),
    "M": ("#...#", "##.##", "#.#.#", "#.#.#", "#...#", "#...#", "#...#"),
    "N": ("#...#", "##..#", "#.#.#", "#..##", "#...#", "#...#", "#...#"),
    "O": (".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "P": ("####.", "#...#", "#...#", "####.", "#....", "#....", "#...."),
    "Q": (".###.", "#...#", "#...#", "#...#", "#.#.#", "#..#.", ".##.#"),
    "R": ("####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"),
    "S": (".####", "#....", "#....", ".###.", "....#", "....#", "####."),
    "T": ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."),
    "U": ("#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "V": ("#...#", "#...#", "#...#", "#...#", "#...#", ".#.#.", "..#.."),
    "W": ("#...#", "#...#", "#...#", "#.#.#", "#.#.#", "##.##", "#...#"),
    "X": ("#...#", ".#.#.", "..#..", "..#..", "..#..", ".#.#.", "#...#"),
    "Y": ("#...#", "#...#", ".#.#.", "..#..", "..#..", "..#..", "..#.."),
    "Z": ("#####", "....#", "...#.", "..#..", ".#...", "#....", "#####"),
}

FONT.update({
    "0": (".###.", "#..##", "#.#.#", "##..#", "#...#", "#...#", ".###."),
    "1": ("..#..", ".##..", "..#..", "..#..", "..#..", "..#..", "#####"),
    "2": (".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"),
    "3": ("####.", "....#", "....#", ".###.", "....#", "....#", "####."),
    "4": ("...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."),
    "5": ("#####", "#....", "####.", "....#", "....#", "#...#", ".###."),
    "6": (".###.", "#....", "#....", "####.", "#...#", "#...#", ".###."),
    "7": ("#####", "....#", "...#.", "..#..", "..#..", "..#..", "..#.."),
    "8": (".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."),
    "9": (".###.", "#...#", "#...#", ".####", "....#", "....#", ".###."),
    " ": (".....", ".....", ".....", ".....", ".....", ".....", "....."),
    ".": (".....", ".....", ".....", ".....", ".....", ".##..", ".##.."),
    ",": (".....", ".....", ".....", ".....", ".##..", ".##..", ".#..."),
    ":": (".....", ".##..", ".##..", ".....", ".##..", ".##..", "....."),
    ";": (".....", ".##..", ".##..", ".....", ".##..", ".##..", ".#..."),
    "-": (".....", ".....", ".....", "#####", ".....", ".....", "....."),
    "'": ("..#..", "..#..", ".#...", ".....", ".....", ".....", "....."),
    "!": ("..#..", "..#..", "..#..", "..#..", "..#..", ".....", "..#.."),
    "?": (".###.", "#...#", "....#", "..##.", "..#..", ".....", "..#.."),
    "/": ("....#", "....#", "...#.", "..#..", ".#...", "#....", "#...."),
    "(": ("...##", "..#..", ".#...", ".#...", ".#...", "..#..", "...##"),
    ")": ("##...", "..#..", "...#.", "...#.", "...#.", "..#..", "##..."),
    "+": (".....", "..#..", "..#..", "#####", "..#..", "..#..", "....."),
    "*": (".....", ".#.#.", "..#..", "#####", "..#..", ".#.#.", "....."),
    "%": ("##..#", "##.#.", "....#", "...#.", "..#..", ".#...", "#..##"),
    "=": (".....", ".....", "#####", ".....", "#####", ".....", "....."),
})

def text_w(s, scale):
    return len(s) * 6 * scale - scale

def draw_text(cv, x, y, s, scale, col, bold=False):
    """Draw string s at (x, y); returns the x just past the text."""
    cx = x
    for ch in s.upper():
        glyph = FONT.get(ch, FONT[" "])
        for row_i, row in enumerate(glyph):
            for col_i, cell in enumerate(row):
                if cell == "#":
                    cv.rect(cx + col_i * scale, y + row_i * scale,
                            scale, scale, col)
                    if bold:
                        cv.rect(cx + col_i * scale + max(1, scale // 3),
                                y + row_i * scale, scale, scale, col)
        cx += 6 * scale
    return cx

def draw_centered(cv, cx, y, s, scale, col, bold=False):
    x = cx - text_w(s, scale) // 2
    draw_text(cv, x, y, s, scale, col, bold)
    return x

def wrap(s, max_chars):
    words, lines, cur = s.split(), [], ""
    for w_ in words:
        trial = (cur + " " + w_).strip()
        if len(trial) <= max_chars:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w_
    if cur:
        lines.append(cur)
    return lines

# ---------------------------------------------------------------- palette

PAPER = (246, 241, 231)
INK = (20, 26, 38)
WHITE = (255, 255, 255)
RED = (178, 34, 44)
BLUE = (29, 78, 166)
TEAL = (0, 110, 110)
GREEN = (34, 110, 60)
ORANGE = (198, 96, 20)
PURPLE = (96, 54, 140)
GREY = (96, 100, 108)
LIGHT = (232, 224, 205)
SKY = (186, 214, 235)
SEA = (64, 120, 178)
SAND = (226, 199, 145)

# ---------------------------------------------------------------- icons
# Small flat illustrations drawn inside a panel's icon box (x, y, size).

def icon_globe(cv, x, y, s):
    """Sun over a globe: the COP31 climate talks."""
    cv.circle(x + s // 4, y + s // 4, s // 6, ORANGE)
    for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (1, -1),
                   (-1, 1), (1, 1)):
        cv.line(x + s // 4 + dx * s // 4, y + s // 4 + dy * s // 4,
                x + s // 4 + dx * (s // 4 + 7), y + s // 4 + dy * (s // 4 + 7),
                ORANGE, 4)
    cx, cy, r = x + s * 5 // 8, y + s * 5 // 8, s // 3
    cv.circle(cx, cy, r, SEA)
    cv.circle(cx - r // 3, cy - r // 4, r // 3, GREEN)
    cv.circle(cx + r // 3, cy + r // 5, r // 4, GREEN)
    cv.circle(cx + r // 6, cy - r // 2, r // 5, GREEN)
    cv.ring(cx, cy, r, 3, INK)

def icon_tanker(cv, x, y, s):
    """Tanker under a missile arc: the Hormuz / Riyadh escalation."""
    hull_y = y + s * 2 // 3
    cv.tri(x + 4, hull_y, x + s - 14, hull_y, x + s - 4, hull_y - s // 6, INK)
    cv.rect(x + 4, hull_y, s - 18, s // 7, INK)
    cv.rect(x + s // 4, hull_y - s // 4, s // 3, s // 4, RED)
    cv.rect(x + s // 4 + 6, hull_y - s // 4 - 10, s // 5, 10, GREY)
    for i in range(4):
        wx = x + 6 + i * (s // 4)
        cv.line(wx, y + s - 8, wx + s // 8, y + s - 14, SEA, 4)
        cv.line(wx + s // 8, y + s - 14, wx + s // 4, y + s - 8, SEA, 4)
    pts = [(x + 6, y + 6), (x + s // 3, y + s // 5), (x + s * 2 // 3, y + 4)]
    for i in range(len(pts) - 1):
        cv.line(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], RED, 4)
    cv.circle(x + s * 2 // 3 + 8, y + 8, 7, ORANGE)
    cv.circle(x + s * 2 // 3 + 8, y + 8, 3, RED)

def icon_crowd(cv, x, y, s):
    """Marchers with a tricolour banner: France's protest weekend."""
    cv.rect(x + s // 3, y + 2, 6, s // 2, INK)
    bx, by, bw, bh = x + s // 3 + 8, y + 2, s // 2, s // 4
    cv.rect(bx, by, bw // 3, bh, BLUE)
    cv.rect(bx + bw // 3, by, bw // 3, bh, WHITE)
    cv.rect(bx + 2 * bw // 3, by, bw - 2 * bw // 3, bh, RED)
    cv.frame(bx, by, bw, bh, 2, INK)
    for i, fx in enumerate((x + 8, x + s // 3, x + s * 2 // 3)):
        hy = y + s * 3 // 5 + (i % 2) * 6
        cv.circle(fx + 10, hy, 9, INK)
        cv.rect(fx + 2, hy + 9, 16, s // 4, INK)

def icon_flood(cv, x, y, s):
    """House in rising water under rain: the Florida floods."""
    hx, hy = x + s // 4, y + s // 3
    cv.tri(hx - 8, hy, hx + s // 4, hy - s // 4, hx + s // 2 + 8, hy, RED)
    cv.rect(hx, hy, s // 2, s // 3, SAND)
    cv.rect(hx + s // 5, hy + s // 8, s // 9, s // 5, INK)
    for i in range(5):
        rx = x + 6 + i * (s // 5)
        cv.line(rx, y + 2, rx - 6, y + s // 5, BLUE, 3)
    wy = y + s * 3 // 4
    cv.rect(x + 2, wy, s - 4, s // 4, SEA)
    for i in range(3):
        wx = x + 8 + i * (s // 3)
        cv.line(wx, wy + 5, wx + s // 9, wy, WHITE, 3)
        cv.line(wx + s // 9, wy, wx + 2 * s // 9, wy + 5, WHITE, 3)

def icon_bottle(cv, x, y, s):
    """Bottle with a warning cross: the Manipur toxic-alcohol deaths."""
    bx, bw = x + s * 3 // 8, s // 4
    cv.rect(bx + bw // 3, y + 2, bw // 3, s // 6, INK)
    cv.rect(bx, y + s // 6, bw, s * 2 // 3, TEAL)
    cv.rect(bx + 5, y + s // 3, bw - 10, s // 3, WHITE)
    cx, cy = bx + bw // 2, y + s // 3 + s // 6
    cv.line(cx - 8, cy - 8, cx + 8, cy + 8, RED, 4)
    cv.line(cx + 8, cy - 8, cx - 8, cy + 8, RED, 4)

def icon_quake(cv, x, y, s):
    """Seismograph trace over mountains: the Peru earthquake."""
    for i, (mx, mh) in enumerate(((x + 2, s // 2), (x + s // 3, s * 2 // 3),
                                  (x + s * 2 // 3, s // 2))):
        cv.tri(mx, y + s, mx + s // 6, y + s - mh, mx + s // 3, y + s, GREY)
    base = y + s * 2 // 3
    pts = [(x + 2, base), (x + s // 5, base), (x + s // 4, base - s // 3),
           (x + s * 2 // 5, base + s // 4), (x + s // 2, base - s // 2),
           (x + s * 3 // 5, base + s // 5), (x + s * 3 // 4, base),
           (x + s - 4, base)]
    for i in range(len(pts) - 1):
        cv.line(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], RED, 4)

# ---------------------------------------------------------------- layout

def panel(cv, x, y, w, h, kicker, accent, headline, sub, icon):
    cv.rect(x, y, w, h, WHITE)
    cv.frame(x, y, w, h, 3, INK)
    cv.rect(x, y, w, 10, accent)
    icon(cv, x + w - 104, y + 18, 88)
    kx = x + 18
    kw = text_w(kicker, 2) + 20
    cv.rect(kx, y + 18, kw, 30, accent)
    draw_text(cv, kx + 10, y + 23, kicker, 2, WHITE, bold=True)
    ty = y + 56
    for line in headline:
        draw_text(cv, x + 18, ty, line, 4, INK, bold=True)
        ty += 42
    ty = y + 140
    for line in sub:
        draw_text(cv, x + 18, ty, line, 3, INK)
        ty += 27

def build():
    cv = Canvas(W, H, PAPER)
    cv.frame(8, 8, W - 16, H - 16, 6, INK)

    # Masthead
    draw_centered(cv, W // 2, 26, "ALL THE NEWS THAT MATTERED, IN ONE PICTURE", 3, GREY)
    draw_centered(cv, W // 2, 62, "THE WORLD IN ONE DAY", 8, INK, bold=True)
    cv.rect(24, 130, W - 48, 52, RED)
    draw_centered(cv, W // 2, 140, "SUNDAY 22 NOVEMBER 2026", 5, WHITE, bold=True)

    # Lead story: COP31
    y = 198
    cv.rect(24, y, W - 48, 200, WHITE)
    cv.frame(24, y, W - 48, 200, 3, INK)
    cv.rect(24, y, W - 48, 10, GREEN)
    icon_globe(cv, 44, y + 30, 150)
    kw = text_w("CLIMATE SUMMIT * ANTALYA, TURKEY", 2) + 20
    cv.rect(224, y + 16, kw, 30, GREEN)
    draw_text(cv, 234, y + 21, "CLIMATE SUMMIT * ANTALYA, TURKEY", 2, WHITE, bold=True)
    draw_text(cv, 224, y + 56, "COP31 GOES INTO OVERTIME", 4, INK, bold=True)
    draw_text(cv, 224, y + 100, "'FOSSIL FUELS' LEFT OUT", 4, RED, bold=True)
    draw_text(cv, 224, y + 144, "SUNDAY DRAFT TEXT SPLITS NEARLY 200", 3, INK)
    draw_text(cv, 224, y + 170, "NATIONS; EU: GOOD DEAL OR NO DEAL", 3, INK)

    # Grid panels
    pw, ph = (W - 48 - 16) // 2, 220
    panel(cv, 24, 414, pw, ph, "MIDDLE EAST * HORMUZ", RED,
          ["TANKERS HIT", "NEAR HORMUZ"],
          ["3 MISSILES AT RIYADH", "DOWNED; TANKERS HIT AND",
           "BAHRAIN SITE SET ABLAZE"],
          icon_tanker)
    panel(cv, 40 + pw, 414, pw, ph, "EUROPE * FRANCE", BLUE,
          ["SIXTH WEEKEND", "OF PROTESTS"],
          ["CROWDS MARCH AGAIN OVER", "LIVING COSTS AND PUBLIC",
           "SERVICES - WEEKEND SIX"],
          icon_crowd)
    panel(cv, 24, 650, pw, ph, "USA * FLORIDA", TEAL,
          ["RECORD FLOOD", "ST JOHNS RIVER"],
          ["18.8 FT AT COCOA, PAST", "THE 1953 MARK; AIRBOAT",
           "RESCUES, CREST MOVES ON"],
          icon_flood)
    panel(cv, 40 + pw, 650, pw, ph, "ASIA * MANIPUR, INDIA", ORANGE,
          ["TAINTED LIQUOR", "KILLS 11 PEOPLE"],
          ["TOXIC ALCOHOL IN", "MANIPUR STATE; 180 AND",
           "MORE IN HOSPITAL"],
          icon_bottle)

    # Peru band
    y = 886
    cv.rect(24, y, W - 48, 88, WHITE)
    cv.frame(24, y, W - 48, 88, 3, INK)
    cv.rect(24, y, W - 48, 10, PURPLE)
    icon_quake(cv, 40, y + 14, 64)
    kw = text_w("AMERICAS * PERU", 2) + 20
    cv.rect(132, y + 14, kw, 30, PURPLE)
    draw_text(cv, 142, y + 19, "AMERICAS * PERU", 2, WHITE, bold=True)
    draw_text(cv, 340, y + 12, "M6.7 QUAKE SHAKES PERU", 4, INK, bold=True)
    draw_text(cv, 340, y + 54, "CENTRAL ANDES, FELT IN LIMA", 3, INK)

    # Sport ticker
    y = 982
    cv.rect(24, y, W - 48, 28, INK)
    draw_centered(cv, W // 2, y + 7,
                  "SPORT * VERSTAPPEN WINS IN LAS VEGAS * SHIMADA WINS FINLANDIA",
                  2, WHITE)
    return cv

def main():
    cv = build()
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "entry.png")
    write_png(path, W, H, cv.px)
    os.chmod(path, 0o644)

if __name__ == "__main__":
    main()
