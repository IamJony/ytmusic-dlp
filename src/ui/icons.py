import math
import tkinter as tk
from PIL import Image, ImageDraw, ImageFilter, ImageTk


def create_youtube_icon(size=64):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    margin = int(size * 0.06)
    radius = int(size * 0.28)
    d.rounded_rectangle(
        [margin, int(size * 0.22), size - margin, int(size * 0.78)],
        radius=radius, fill="#ff0033"
    )
    cx, cy = size / 2, size / 2
    t = size * 0.16
    d.polygon([
        (cx - t * 0.6, cy - t),
        (cx - t * 0.6, cy + t),
        (cx + t, cy),
    ], fill="white")
    return ImageTk.PhotoImage(img)


class IconFactory:
    _cache = {}

    @classmethod
    def get(cls, name, size=18, color="#ffffff", glow=False):
        key = (name, size, color, glow)
        if key in cls._cache:
            return cls._cache[key]
        img = cls._draw(name, size, color)
        if glow:
            glow_layer = img.filter(ImageFilter.GaussianBlur(2))
            img = Image.alpha_composite(glow_layer, img)
        photo = ImageTk.PhotoImage(img)
        cls._cache[key] = photo
        return photo

    @classmethod
    def clear(cls):
        """No-op: mantener referencias evita destruir PhotoImages en uso."""
        pass

    @classmethod
    def hard_clear(cls):
        cls._cache.clear()

    @classmethod
    def _draw(cls, name, size, color):
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        w = max(1, size // 9)

        if name == "play":
            d.polygon([(size*0.28, size*0.18), (size*0.28, size*0.82),
                       (size*0.82, size*0.5)], fill=color)
        elif name == "pause":
            d.rectangle([size*0.30, size*0.20, size*0.44, size*0.80], fill=color)
            d.rectangle([size*0.56, size*0.20, size*0.70, size*0.80], fill=color)
        elif name == "stop":
            d.rectangle([size*0.28, size*0.28, size*0.72, size*0.72], fill=color)
        elif name == "prev":
            d.polygon([(size*0.72, size*0.18), (size*0.72, size*0.82),
                       (size*0.32, size*0.5)], fill=color)
            d.rectangle([size*0.22, size*0.20, size*0.30, size*0.80], fill=color)
        elif name == "next":
            d.polygon([(size*0.28, size*0.18), (size*0.28, size*0.82),
                       (size*0.68, size*0.5)], fill=color)
            d.rectangle([size*0.70, size*0.20, size*0.78, size*0.80], fill=color)
        elif name == "search":
            d.ellipse([size*0.18, size*0.18, size*0.72, size*0.72],
                      outline=color, width=w)
            d.line([size*0.65, size*0.65, size*0.86, size*0.86],
                   fill=color, width=w)
        elif name == "star":
            cx, cy, r = size*0.5, size*0.52, size*0.36
            pts = []
            for i in range(10):
                ang = math.pi/2 + i * math.pi/5
                rad = r if i % 2 == 0 else r*0.45
                pts.append((cx + rad*math.cos(ang), cy - rad*math.sin(ang)))
            d.polygon(pts, fill=color)
        elif name == "heart":
            cx, cy, r = size*0.5, size*0.5, size*0.3
            d.polygon([
                (cx, cy + r),
                (cx - r, cy - r*0.3),
                (cx - r*0.5, cy - r),
                (cx, cy - r*0.6),
                (cx + r*0.5, cy - r),
                (cx + r, cy - r*0.3),
            ], fill=color)
        elif name == "plus":
            d.line([size*0.5, size*0.20, size*0.5, size*0.80], fill=color, width=w+1)
            d.line([size*0.20, size*0.5, size*0.80, size*0.5], fill=color, width=w+1)
        elif name == "download":
            d.line([size*0.5, size*0.15, size*0.5, size*0.65], fill=color, width=w+1)
            d.polygon([(size*0.30, size*0.55), (size*0.70, size*0.55),
                       (size*0.5, size*0.80)], fill=color)
            d.line([size*0.20, size*0.88, size*0.80, size*0.88], fill=color, width=w+1)
        elif name == "upload":
            d.line([size*0.5, size*0.85, size*0.5, size*0.35], fill=color, width=w+1)
            d.polygon([(size*0.30, size*0.45), (size*0.70, size*0.45),
                       (size*0.5, size*0.20)], fill=color)
            d.line([size*0.20, size*0.12, size*0.80, size*0.12], fill=color, width=w+1)
        elif name == "volume":
            d.polygon([(size*0.15, size*0.40), (size*0.15, size*0.60),
                       (size*0.35, size*0.60), (size*0.55, size*0.80),
                       (size*0.55, size*0.20), (size*0.35, size*0.40)], fill=color)
            d.arc([size*0.45, size*0.25, size*0.85, size*0.75],
                  start=-60, end=60, fill=color, width=w)
        elif name == "trash":
            d.rectangle([size*0.25, size*0.30, size*0.75, size*0.85],
                        outline=color, width=w)
            d.line([size*0.15, size*0.28, size*0.85, size*0.28], fill=color, width=w)
            d.line([size*0.40, size*0.18, size*0.60, size*0.18], fill=color, width=w)
            d.line([size*0.42, size*0.42, size*0.42, size*0.72], fill=color, width=w)
            d.line([size*0.58, size*0.42, size*0.58, size*0.72], fill=color, width=w)
        elif name == "edit":
            d.polygon([(size*0.15, size*0.85), (size*0.22, size*0.60),
                       (size*0.70, size*0.12), (size*0.88, size*0.30),
                       (size*0.40, size*0.78)], fill=color)
        elif name == "folder":
            d.polygon([(size*0.10, size*0.25), (size*0.45, size*0.25),
                       (size*0.55, size*0.40), (size*0.90, size*0.40),
                       (size*0.90, size*0.85), (size*0.10, size*0.85)], fill=color)
        elif name == "music":
            d.ellipse([size*0.15, size*0.65, size*0.40, size*0.85], fill=color)
            d.ellipse([size*0.55, size*0.55, size*0.80, size*0.75], fill=color)
            d.line([size*0.38, size*0.75, size*0.38, size*0.20], fill=color, width=w)
            d.line([size*0.78, size*0.65, size*0.78, size*0.15], fill=color, width=w)
            d.line([size*0.38, size*0.20, size*0.78, size*0.15], fill=color, width=w)
        elif name == "palette":
            d.ellipse([size*0.10, size*0.10, size*0.90, size*0.90],
                      outline=color, width=w)
            d.ellipse([size*0.30, size*0.30, size*0.40, size*0.40], fill=color)
            d.ellipse([size*0.55, size*0.30, size*0.65, size*0.40], fill=color)
            d.ellipse([size*0.42, size*0.55, size*0.52, size*0.65], fill=color)
        elif name == "shuffle":
            d.line([size*0.15, size*0.35, size*0.55, size*0.35], fill=color, width=w)
            d.line([size*0.55, size*0.35, size*0.85, size*0.65], fill=color, width=w)
            d.line([size*0.15, size*0.65, size*0.55, size*0.65], fill=color, width=w)
            d.line([size*0.55, size*0.65, size*0.85, size*0.35], fill=color, width=w)
            d.polygon([(size*0.70, size*0.55), (size*0.86, size*0.65),
                       (size*0.86, size*0.50)], fill=color)
            d.polygon([(size*0.70, size*0.45), (size*0.86, size*0.35),
                       (size*0.86, size*0.50)], fill=color)
        elif name == "check":
            d.line([size*0.20, size*0.50, size*0.42, size*0.72], fill=color, width=w+2)
            d.line([size*0.42, size*0.72, size*0.82, size*0.28], fill=color, width=w+2)
        elif name == "x":
            d.line([size*0.25, size*0.25, size*0.75, size*0.75], fill=color, width=w+1)
            d.line([size*0.75, size*0.25, size*0.25, size*0.75], fill=color, width=w+1)
        elif name == "repeat":
            d.arc([size*0.20, size*0.20, size*0.80, size*0.80],
                  start=45, end=315, fill=color, width=w+1)
            d.polygon([(size*0.78, size*0.15), (size*0.88, size*0.28),
                       (size*0.72, size*0.28)], fill=color)
        elif name == "menu":
            for y in (0.3, 0.5, 0.7):
                d.line([size*0.20, size*y, size*0.80, size*y], fill=color, width=w+1)
        return img
