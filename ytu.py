
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
import threading
import json
import os
import random
import time
import webbrowser
import yt_dlp
import mpv
from PIL import Image, ImageDraw, ImageTk

from themes import THEMES, THEME_ORDER


YT_FILTER_ALL       = ""
YT_FILTER_SONGS     = "EgIQAQ%3D%3D"
YT_FILTER_VIDEOS    = "EgIQAQ%3D%3D"
YT_FILTER_PLAYLISTS = "EgIQAw%3D%3D"

PAGE_SIZE = 30
DATA_FILE = os.path.join(os.path.expanduser("~"), ".yt_music_player_data.json")
SETTINGS_FILE = os.path.join(os.path.expanduser("~"), ".yt_music_player_settings.json")

GITHUB_URL = "https://github.com/IamJony"


# ---------- Icono de YouTube para la ventana ----------
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
    def get(cls, name, size=18, color="#ffffff"):
        key = (name, size, color)
        if key in cls._cache:
            return cls._cache[key]
        img = cls._draw(name, size, color)
        photo = ImageTk.PhotoImage(img)
        cls._cache[key] = photo
        return photo

    @classmethod
    def clear(cls):
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
            import math
            cx, cy, r = size*0.5, size*0.52, size*0.36
            pts = []
            for i in range(10):
                ang = math.pi/2 + i * math.pi/5
                rad = r if i % 2 == 0 else r*0.45
                pts.append((cx + rad*math.cos(ang), cy - rad*math.sin(ang)))
            d.polygon(pts, fill=color)
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
            d.line([size*0.15, size*0.35, size*0.55, size*0.35],
                   fill=color, width=w)
            d.line([size*0.55, size*0.35, size*0.85, size*0.65],
                   fill=color, width=w)
            d.line([size*0.15, size*0.65, size*0.55, size*0.65],
                   fill=color, width=w)
            d.line([size*0.55, size*0.65, size*0.85, size*0.35],
                   fill=color, width=w)
            d.polygon([(size*0.70, size*0.55), (size*0.86, size*0.65),
                       (size*0.86, size*0.50)], fill=color)
            d.polygon([(size*0.70, size*0.45), (size*0.86, size*0.35),
                       (size*0.86, size*0.50)], fill=color)
        return img


class YouTubeMusicPlayer:
    def __init__(self, root):
        self.root = root
        self.root.title("ytmusic-dlp  ·  by IamJony")
        self.root.geometry("1000x740")
        self.root.configure(bg="#0a0e14")

        try:
            self._window_icon = create_youtube_icon(64)
            self.root.iconphoto(True, self._window_icon)
        except Exception as e:
            print(f"No se pudo aplicar el icono: {e}")

        self.current_theme = self._load_theme_setting()
        self.colors = THEMES[self.current_theme]

        self.favorites = []
        self.local_playlists = {}
        self._load_data()

        self.playlist = []
        self.current_index = -1
        self.is_paused = False
        self.shuffle_mode = False
        self.shuffle_history = []
        self._shuffle_btn = None

        self.current_query = ""
        self.current_sp = ""
        self.loaded_count = 0
        self.loading = False

        self._themed_widgets = []
        self._icon_widgets = []
        self._theme_menu_open = False

        self.player = mpv.MPV(
            ytdl=False, video=False, really_quiet=True,
            input_default_bindings=False, input_vo_keyboard=False,
        )
        self._ended = False
        self._last_duration = 0.0
        self._buffering = False
        self._idle_strikes = 0
        self._starting = False
        self._started_at = 0.0

        self._seeking = False
        self._seek_value = 0.0

        @self.player.property_observer('eof-reached')
        def _on_eof(_n, v):
            if v and not self._starting:
                self.root.after(150, self._on_track_end)

        @self.player.property_observer('core-idle')
        def _on_idle(_n, v):
            if v and not self._starting and self.current_index >= 0 and not self.is_paused:
                self.root.after(150, self._on_track_end)

        self._build_ui()
        self.apply_theme(self.current_theme, save=False)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    # ---------------- Ajustes ----------------
    def _load_theme_setting(self):
        try:
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    s = json.load(f)
                    t = s.get("theme", "Alienware")
                    if t in THEMES:
                        return t
        except Exception:
            pass
        return "Alienware"

    def _save_theme_setting(self):
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump({"theme": self.current_theme}, f)
        except Exception:
            pass

    def C(self, key):
        return self.colors.get(key, "#ffffff")

    def _register(self, widget, **color_map):
        self._themed_widgets.append((widget, color_map))
        return widget

    def apply_theme(self, name, save=True):
        if name not in THEMES:
            return
        self.current_theme = name
        self.colors = THEMES[name]
        if save:
            self._save_theme_setting()

        self.root.configure(bg=self.C("BG"))
        IconFactory.clear()

        for widget, mapping in self._themed_widgets:
            try:
                widget.configure(**{opt: self.C(key) for opt, key in mapping.items()})
            except Exception:
                pass

        for widget, icon_name, size, color_key in self._icon_widgets:
            try:
                icon = IconFactory.get(icon_name, size, self.C(color_key))
                widget.configure(image=icon)
                widget.image = icon
            except Exception:
                pass

        for menu in (self.pl_menu, self.lb_menu, self.theme_menu):
            try:
                menu.configure(bg=self.C("BG_PANEL"), fg=self.C("FG"),
                               activebackground=self.C("ACCENT"),
                               activeforeground=self.C("BG"))
            except Exception:
                pass

        try:
            palette_icon = IconFactory.get("palette", 15, self.C("ACCENT"))
            self.theme_btn.configure(image=palette_icon,
                                     text=f"  Tema: {name}")
            self.theme_btn.image = palette_icon
        except Exception:
            pass

        self._refresh_theme_menu_checks()
        self._refresh_shuffle_btn()

        try:
            self.progress_canvas.configure(bg=self.C("BG"))
            self._draw_progress()
        except Exception:
            pass

        style = ttk.Style()
        style.configure("AW.TCombobox",
                        fieldbackground=self.C("BG_INPUT"),
                        background=self.C("BG_INPUT"),
                        foreground=self.C("FG"),
                        arrowcolor=self.C("ACCENT"),
                        bordercolor=self.C("ACCENT_DARK"),
                        lightcolor=self.C("BG_INPUT"),
                        darkcolor=self.C("BG_INPUT"))
        style.map("AW.TCombobox",
                  fieldbackground=[("readonly", self.C("BG_INPUT"))],
                  foreground=[("readonly", self.C("FG"))],
                  selectbackground=[("readonly", self.C("BG_INPUT"))],
                  selectforeground=[("readonly", self.C("FG"))])

        self.status.config(text=f"Tema: {name}")

    # ---------------- Persistencia ----------------
    def _load_data(self):
        try:
            if os.path.exists(DATA_FILE):
                with open(DATA_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.favorites = data.get("favorites", [])
                    self.local_playlists = data.get("local_playlists", {})
        except Exception as e:
            print(f"No se pudo cargar datos: {e}")

    def _save_data(self):
        try:
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump({
                    "favorites": self.favorites,
                    "local_playlists": self.local_playlists,
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"No se pudo guardar datos: {e}")

    # ---------------- Export / Import ----------------
    def export_data(self):
        path = filedialog.asksaveasfilename(
            title="Exportar biblioteca", defaultextension=".json",
            filetypes=[("JSON", "*.json"), ("Todos los archivos", "*.*")],
            initialfile="music_backup.json")
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"favorites": self.favorites,
                           "local_playlists": self.local_playlists,
                           "version": 1}, f, ensure_ascii=False, indent=2)
            self.status.config(text=f"Biblioteca exportada a {os.path.basename(path)}")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo exportar: {e}")

    def import_data(self):
        path = filedialog.askopenfilename(
            title="Importar biblioteca",
            filetypes=[("JSON", "*.json"), ("Todos los archivos", "*.*")])
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo leer el archivo: {e}")
            return
        favs = data.get("favorites", [])
        pls = data.get("local_playlists", {})
        if not favs and not pls:
            messagebox.showinfo("Vacio", "El archivo no contiene favoritos ni playlists.")
            return
        choice = messagebox.askyesnocancel(
            "Importar",
            "Como quieres importar?\n\n"
            "Si = Fusionar con lo actual\n"
            "No = Reemplazar todo\n"
            "Cancelar = Cancelar")
        if choice is None:
            return
        if choice:
            existing_urls = {f["url"] for f in self.favorites}
            added_favs = 0
            for f in favs:
                if f.get("url") and f["url"] not in existing_urls:
                    self.favorites.append(f)
                    existing_urls.add(f["url"])
                    added_favs += 1
            added_pls = 0
            for name, items in pls.items():
                if name in self.local_playlists:
                    existing = {x["url"] for x in self.local_playlists[name]}
                    for it in items:
                        if it.get("url") and it["url"] not in existing:
                            self.local_playlists[name].append(it)
                            existing.add(it["url"])
                else:
                    self.local_playlists[name] = items
                    added_pls += 1
            msg = f"Fusionado: {added_favs} favoritos nuevos, {added_pls} playlists nuevas."
        else:
            self.favorites = favs
            self.local_playlists = pls
            msg = f"Reemplazado: {len(favs)} favoritos, {len(pls)} playlists."
        self._save_data()
        self._refresh_playlists_sidebar()
        messagebox.showinfo("Importar", msg)

    # ---------------- UI ----------------
    def _build_ui(self):
        style = ttk.Style()
        style.theme_use("clam")

        menubar_frame = tk.Frame(self.root, bg=self.C("BG_PANEL"), height=42)
        menubar_frame.pack(fill="x")
        menubar_frame.pack_propagate(False)
        self._register(menubar_frame, bg="BG_PANEL")

        def make_icon_btn(parent, icon_name, text, cmd, color_key="ACCENT",
                          bg_key="BG_PANEL", size=16):
            icon = IconFactory.get(icon_name, size, self.C(color_key))
            b = tk.Button(parent, text=f"  {text}", image=icon, compound="left",
                          command=cmd, bg=self.C(bg_key), fg=self.C(color_key),
                          relief="flat",
                          activebackground=self.C("BG_INPUT"),
                          activeforeground=self.C(color_key),
                          font=("Segoe UI", 9), padx=12, bd=0)
            b.image = icon
            self._register(b, bg=bg_key, fg=color_key,
                           activebackground="BG_INPUT",
                           activeforeground=color_key)
            self._icon_widgets.append((b, icon_name, size, color_key))
            return b

        make_icon_btn(menubar_frame, "upload", "Exportar", self.export_data).pack(side="left")
        make_icon_btn(menubar_frame, "download", "Importar", self.import_data).pack(side="left")

        palette_icon = IconFactory.get("palette", 15, self.C("ACCENT"))
        self.theme_btn = tk.Button(
            menubar_frame,
            text=f"  Tema: {self.current_theme}",
            image=palette_icon, compound="left",
            command=self._open_theme_menu,
            bg=self.C("BG_PANEL"), fg=self.C("ACCENT"),
            relief="flat",
            activebackground=self.C("BG_INPUT"),
            activeforeground=self.C("ACCENT"),
            font=("Segoe UI", 9), padx=12, bd=0)
        self.theme_btn.image = palette_icon
        self.theme_btn.pack(side="left", padx=(16, 0))
        self._register(self.theme_btn, bg="BG_PANEL", fg="ACCENT",
                       activebackground="BG_INPUT", activeforeground="ACCENT")

        self.theme_menu = tk.Menu(self.root, tearoff=0,
                                  bg=self.C("BG_PANEL"), fg=self.C("FG"),
                                  activebackground=self.C("ACCENT"),
                                  activeforeground=self.C("BG"), bd=0)
        for tname in THEME_ORDER:
            self.theme_menu.add_command(
                label=tname,
                command=lambda n=tname: self._select_theme(n))
        self.theme_menu.add_separator()
        self.theme_menu.add_command(label="Aleatorio", command=self._random_theme)

        self.root.bind("<Button-1>", self._maybe_close_theme_menu, add="+")
        self.root.bind("<FocusOut>", lambda e: self._close_theme_menu(), add="+")
        self.root.bind("<Escape>", lambda e: self._close_theme_menu(), add="+")

        accent_line = tk.Frame(self.root, bg=self.C("ACCENT"), height=2)
        accent_line.pack(fill="x")
        self._register(accent_line, bg="ACCENT")

        search_frame = tk.Frame(self.root, bg=self.C("BG"))
        search_frame.pack(fill="x", padx=12, pady=10)
        self._register(search_frame, bg="BG")

        lbl = tk.Label(search_frame, text="Buscar:", fg=self.C("FG"), bg=self.C("BG"),
                       font=("Segoe UI", 11))
        lbl.pack(side="left")
        self._register(lbl, fg="FG", bg="BG")

        self.search_entry = tk.Entry(search_frame, font=("Segoe UI", 11),
                                     bg=self.C("BG_INPUT"), fg=self.C("FG"),
                                     insertbackground=self.C("ACCENT"),
                                     relief="flat", highlightthickness=1,
                                     highlightbackground=self.C("ACCENT_DARK"),
                                     highlightcolor=self.C("ACCENT"))
        self.search_entry.pack(side="left", fill="x", expand=True, padx=8, ipady=5)
        self.search_entry.bind("<Return>", lambda e: self.search())
        self._register(self.search_entry, bg="BG_INPUT", fg="FG",
                       insertbackground="ACCENT",
                       highlightbackground="ACCENT_DARK",
                       highlightcolor="ACCENT")

        self.search_type = tk.StringVar(value="Todo")
        type_menu = ttk.Combobox(search_frame, textvariable=self.search_type,
                                 values=["Todo", "Canciones", "Videos", "Playlists"],
                                 state="readonly", width=11, font=("Segoe UI", 10),
                                 style="AW.TCombobox")
        type_menu.pack(side="left", padx=(0, 8))

        search_icon = IconFactory.get("search", 14, self.C("BG"))
        sb = tk.Button(search_frame, text="  Buscar", image=search_icon, compound="left",
                       command=self.search, bg=self.C("ACCENT"), fg=self.C("BG"),
                       relief="flat", activebackground=self.C("ACCENT_DARK"),
                       activeforeground=self.C("BG"),
                       font=("Segoe UI", 10, "bold"), padx=14, bd=0)
        sb.image = search_icon
        sb.pack(side="left")
        self._register(sb, bg="ACCENT", fg="BG",
                       activebackground="ACCENT_DARK", activeforeground="BG")
        self._icon_widgets.append((sb, "search", 14, "BG"))

        body = tk.Frame(self.root, bg=self.C("BG"))
        body.pack(fill="both", expand=True, padx=12, pady=5)
        self._register(body, bg="BG")

        sidebar = tk.Frame(body, bg=self.C("BG_PANEL"), width=250,
                           highlightthickness=1,
                           highlightbackground=self.C("ACCENT_DARK"))
        sidebar.pack(side="left", fill="y", padx=(0, 8))
        sidebar.pack_propagate(False)
        self._register(sidebar, bg="BG_PANEL", highlightbackground="ACCENT_DARK")

        lib_lbl = tk.Label(sidebar, text="BIBLIOTECA", fg=self.C("ACCENT"),
                           bg=self.C("BG_PANEL"), font=("Segoe UI", 10, "bold"))
        lib_lbl.pack(pady=(10, 4), anchor="w", padx=10)
        self._register(lib_lbl, fg="ACCENT", bg="BG_PANEL")

        star_icon = IconFactory.get("star", 16, self.C("OK"))
        self.fav_btn = tk.Button(sidebar, text=f"  Favoritos ({len(self.favorites)})",
                                 image=star_icon, compound="left",
                                 command=self.show_favorites,
                                 bg=self.C("BG_INPUT"), fg=self.C("OK"),
                                 relief="flat", anchor="w", padx=10, pady=6,
                                 activebackground=self.C("BG"),
                                 activeforeground=self.C("OK"),
                                 font=("Segoe UI", 10), bd=0)
        self.fav_btn.image = star_icon
        self.fav_btn.pack(fill="x", padx=6, pady=2)
        self._register(self.fav_btn, bg="BG_INPUT", fg="OK",
                       activebackground="BG", activeforeground="OK")
        self._icon_widgets.append((self.fav_btn, "star", 16, "OK"))

        sep = tk.Frame(sidebar, bg=self.C("ACCENT_DARK"), height=1)
        sep.pack(fill="x", padx=10, pady=6)
        self._register(sep, bg="ACCENT_DARK")

        header = tk.Frame(sidebar, bg=self.C("BG_PANEL"))
        header.pack(fill="x", padx=6)
        self._register(header, bg="BG_PANEL")

        pl_lbl = tk.Label(header, text="MIS PLAYLISTS", fg=self.C("ACCENT"),
                          bg=self.C("BG_PANEL"), font=("Segoe UI", 10, "bold"))
        pl_lbl.pack(side="left", padx=4)
        self._register(pl_lbl, fg="ACCENT", bg="BG_PANEL")

        plus_icon = IconFactory.get("plus", 14, self.C("BG"))
        pb = tk.Button(header, image=plus_icon, command=self.create_playlist,
                       bg=self.C("ACCENT"), relief="flat",
                       activebackground=self.C("ACCENT_DARK"),
                       width=24, height=24, bd=0)
        pb.image = plus_icon
        pb.pack(side="right")
        self._register(pb, bg="ACCENT", activebackground="ACCENT_DARK")
        self._icon_widgets.append((pb, "plus", 14, "BG"))

        self.pl_listbox = tk.Listbox(sidebar, bg=self.C("BG_PANEL"), fg=self.C("FG"),
                                     selectbackground=self.C("SELECT_BG"),
                                     selectforeground=self.C("SELECT_FG"),
                                     font=("Segoe UI", 10), relief="flat",
                                     activestyle="none", highlightthickness=0, bd=0)
        self.pl_listbox.pack(fill="both", expand=True, padx=6, pady=6)
        self.pl_listbox.bind("<Double-Button-1>", lambda e: self.open_local_playlist())
        self.pl_listbox.bind("<Button-3>", self._playlist_context_menu)
        self._register(self.pl_listbox, bg="BG_PANEL", fg="FG",
                       selectbackground="SELECT_BG", selectforeground="SELECT_FG")

        self.pl_menu = tk.Menu(self.root, tearoff=0,
                               bg=self.C("BG_PANEL"), fg=self.C("FG"),
                               activebackground=self.C("ACCENT"),
                               activeforeground=self.C("BG"), bd=0)
        self.pl_menu.add_command(label="Reproducir",
                                 image=IconFactory.get("play", 14, self.C("ACCENT")),
                                 compound="left", command=self.open_local_playlist)
        self.pl_menu.add_command(label="Renombrar",
                                 image=IconFactory.get("edit", 14, self.C("FG")),
                                 compound="left", command=self.rename_playlist)
        self.pl_menu.add_command(label="Eliminar",
                                 image=IconFactory.get("trash", 14, self.C("DANGER")),
                                 compound="left", command=self.delete_playlist)
        self._pl_menu_icons = [
            IconFactory.get("play", 14, self.C("ACCENT")),
            IconFactory.get("edit", 14, self.C("FG")),
            IconFactory.get("trash", 14, self.C("DANGER")),
        ]

        self._refresh_playlists_sidebar()

        right = tk.Frame(body, bg=self.C("BG"))
        right.pack(side="left", fill="both", expand=True)
        self._register(right, bg="BG")

        list_frame = tk.Frame(right, bg=self.C("BG"))
        list_frame.pack(fill="both", expand=True)
        self._register(list_frame, bg="BG")

        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")

        self.listbox = tk.Listbox(list_frame, bg=self.C("BG_INPUT"), fg=self.C("FG"),
                                  selectbackground=self.C("SELECT_BG"),
                                  selectforeground=self.C("SELECT_FG"),
                                  font=("Segoe UI", 10), relief="flat",
                                  yscrollcommand=scrollbar.set, activestyle="none",
                                  highlightthickness=1,
                                  highlightbackground=self.C("ACCENT_DARK"))
        self.listbox.pack(fill="both", expand=True)
        scrollbar.config(command=self.listbox.yview)
        self.listbox.bind("<Double-Button-1>", lambda e: self.play_selected())
        self.listbox.bind("<Button-3>", self._listbox_context_menu)
        self._register(self.listbox, bg="BG_INPUT", fg="FG",
                       selectbackground="SELECT_BG", selectforeground="SELECT_FG",
                       highlightbackground="ACCENT_DARK")

        self.lb_menu = tk.Menu(self.root, tearoff=0,
                               bg=self.C("BG_PANEL"), fg=self.C("FG"),
                               activebackground=self.C("ACCENT"),
                               activeforeground=self.C("BG"), bd=0)
        self.lb_menu.add_command(label="Reproducir",
                                 image=IconFactory.get("play", 14, self.C("ACCENT")),
                                 compound="left", command=self.play_selected)
        self.lb_menu.add_command(label="Anadir/Quitar favorito",
                                 image=IconFactory.get("star", 14, self.C("OK")),
                                 compound="left", command=self.toggle_favorite_selected)
        self.lb_menu.add_separator()
        self.lb_menu.add_command(label="Anadir a playlist local...",
                                 image=IconFactory.get("plus", 14, self.C("ACCENT")),
                                 compound="left",
                                 command=self.add_selected_to_local_playlist)
        self.lb_menu.add_command(label="Guardar playlist completa...",
                                 image=IconFactory.get("folder", 14, self.C("FG")),
                                 compound="left",
                                 command=self.save_playlist_as_local)
        self._lb_menu_icons = [
            IconFactory.get("play", 14, self.C("ACCENT")),
            IconFactory.get("star", 14, self.C("OK")),
            IconFactory.get("plus", 14, self.C("ACCENT")),
            IconFactory.get("folder", 14, self.C("FG")),
        ]

        load_frame = tk.Frame(right, bg=self.C("BG"))
        load_frame.pack(fill="x", pady=(4, 0))
        self._register(load_frame, bg="BG")

        dl_icon = IconFactory.get("download", 14, self.C("ACCENT"))
        self.load_more_btn = tk.Button(load_frame,
                                       text="  Cargar mas resultados",
                                       image=dl_icon, compound="left",
                                       command=self.load_more,
                                       bg=self.C("BG_INPUT"), fg=self.C("ACCENT"),
                                       relief="flat",
                                       activebackground=self.C("ACCENT"),
                                       activeforeground=self.C("BG"),
                                       font=("Segoe UI", 10, "bold"), pady=4,
                                       state="disabled", bd=0)
        self.load_more_btn.image = dl_icon
        self.load_more_btn.pack(fill="x")
        self._register(self.load_more_btn, bg="BG_INPUT", fg="ACCENT",
                       activebackground="ACCENT", activeforeground="BG")
        self._icon_widgets.append((self.load_more_btn, "download", 14, "ACCENT"))

        music_icon = IconFactory.get("music", 16, self.C("OK"))
        self.now_playing = tk.Label(self.root, text="  Nada reproduciendose",
                                    image=music_icon, compound="left",
                                    fg=self.C("OK"), bg=self.C("BG"),
                                    font=("Segoe UI", 10, "italic"),
                                    wraplength=900)
        self.now_playing.image = music_icon
        self.now_playing.pack(pady=(10, 5))
        self._register(self.now_playing, fg="OK", bg="BG")
        self._icon_widgets.append((self.now_playing, "music", 16, "OK"))

        progress_frame = tk.Frame(self.root, bg=self.C("BG"))
        progress_frame.pack(fill="x", padx=12)
        self._register(progress_frame, bg="BG")

        self.time_label = tk.Label(progress_frame, text="00:00 / 00:00",
                                   fg=self.C("FG_DIM"), bg=self.C("BG"),
                                   font=("Consolas", 9), width=13, anchor="w")
        self.time_label.pack(side="left")
        self._register(self.time_label, fg="FG_DIM", bg="BG")

        self.progress_canvas = tk.Canvas(progress_frame, height=18,
                                          bg=self.C("BG"), highlightthickness=0,
                                          bd=0, cursor="hand2")
        self.progress_canvas.pack(side="left", fill="x", expand=True, padx=8)
        self._register(self.progress_canvas, bg="BG")

        self.progress_canvas.bind("<Configure>", lambda e: self._draw_progress())
        self.progress_canvas.bind("<Button-1>", self._on_progress_press)
        self.progress_canvas.bind("<B1-Motion>", self._on_progress_drag)
        self.progress_canvas.bind("<ButtonRelease-1>", self._on_progress_release)

        controls = tk.Frame(self.root, bg=self.C("BG"))
        controls.pack(pady=10)
        self._register(controls, bg="BG")

        def icon_only_btn(parent, icon_name, cmd, color_key="ACCENT", size=22):
            icon = IconFactory.get(icon_name, size, self.C(color_key))
            b = tk.Button(parent, image=icon, command=cmd,
                          bg=self.C("BG_INPUT"), relief="flat",
                          activebackground=self.C("ACCENT"),
                          activeforeground=self.C("BG"),
                          width=44, height=36, bd=0)
            b.image = icon
            self._register(b, bg="BG_INPUT", activebackground="ACCENT",
                           activeforeground="BG")
            self._icon_widgets.append((b, icon_name, size, color_key))
            return b

        icon_only_btn(controls, "prev", self.prev_song).grid(row=0, column=0, padx=4)

        play_icon = IconFactory.get("play", 26, self.C("BG"))
        self.play_btn = tk.Button(controls, image=play_icon,
                                  command=self.toggle_play,
                                  bg=self.C("ACCENT"), relief="flat",
                                  activebackground=self.C("ACCENT_DARK"),
                                  width=50, height=40, bd=0)
        self.play_btn.image_play = play_icon
        self.play_btn.grid(row=0, column=1, padx=4)
        self._register(self.play_btn, bg="ACCENT", activebackground="ACCENT_DARK")

        icon_only_btn(controls, "next", self.next_song).grid(row=0, column=2, padx=4)
        icon_only_btn(controls, "stop", self.stop_song).grid(row=0, column=3, padx=4)

        shuffle_icon = IconFactory.get("shuffle", 22, self.C("ACCENT"))
        self._shuffle_btn = tk.Button(controls, image=shuffle_icon,
                                      command=self.toggle_shuffle,
                                      bg=self.C("BG_INPUT"), relief="flat",
                                      activebackground=self.C("ACCENT"),
                                      activeforeground=self.C("BG"),
                                      width=44, height=36, bd=0)
        self._shuffle_btn.image = shuffle_icon
        self._shuffle_btn.grid(row=0, column=4, padx=(12, 4))
        self._register(self._shuffle_btn, bg="BG_INPUT",
                       activebackground="ACCENT", activeforeground="BG")
        self._icon_widgets.append((self._shuffle_btn, "shuffle", 22, "ACCENT"))

        vol_frame = tk.Frame(controls, bg=self.C("BG"))
        vol_frame.grid(row=0, column=5, padx=(20, 4))
        self._register(vol_frame, bg="BG")

        vol_icon = IconFactory.get("volume", 16, self.C("FG_DIM"))
        vol_label = tk.Label(vol_frame, image=vol_icon, bg=self.C("BG"))
        vol_label.image = vol_icon
        vol_label.pack(side="left")
        self._register(vol_label, bg="BG")
        self._icon_widgets.append((vol_label, "volume", 16, "FG_DIM"))

        self.volume = tk.Scale(vol_frame, from_=0, to=100, orient="horizontal",
                               bg=self.C("BG"), fg=self.C("ACCENT"),
                               troughcolor=self.C("BG_INPUT"),
                               highlightthickness=0, showvalue=False, length=120,
                               command=self._on_volume,
                               activebackground=self.C("ACCENT"), bd=0)
        self.volume.set(80)
        self.volume.pack(side="left", padx=4)
        self.player.volume = 80
        self._register(self.volume, bg="BG", fg="ACCENT",
                       troughcolor="BG_INPUT", activebackground="ACCENT")

        bottom_bar = tk.Frame(self.root, bg=self.C("BG"))
        bottom_bar.pack(fill="x", padx=12, pady=(5, 8))
        self._register(bottom_bar, bg="BG")

        self.github_link = tk.Label(bottom_bar,
                                    text=f"by IamJony  ({GITHUB_URL})",
                                    fg=self.C("FG_DIM"), bg=self.C("BG"),
                                    font=("Segoe UI", 8),
                                    cursor="hand2")
        self.github_link.pack(side="right")
        self.github_link.bind("<Button-1>",
                              lambda e: webbrowser.open(GITHUB_URL))
        self.github_link.bind("<Enter>",
                              lambda e: self.github_link.config(fg=self.C("ACCENT")))
        self.github_link.bind("<Leave>",
                              lambda e: self.github_link.config(fg=self.C("FG_DIM")))
        self._register(self.github_link, fg="FG_DIM", bg="BG")

        self.status = tk.Label(bottom_bar, text="Listo", fg=self.C("FG_DIM"),
                               bg=self.C("BG"),
                               font=("Segoe UI", 9), anchor="w")
        self.status.pack(side="left")
        self._register(self.status, fg="FG_DIM", bg="BG")

        self._icon_pause = IconFactory.get("pause", 26, self.C("BG"))
        self._icon_play  = IconFactory.get("play", 26, self.C("BG"))

        self._update_progress()

    # ---------------- Menú de temas ----------------
    def _open_theme_menu(self):
        if self._theme_menu_open:
            self._close_theme_menu()
            return
        x = self.theme_btn.winfo_rootx()
        y = self.theme_btn.winfo_rooty() + self.theme_btn.winfo_height()
        try:
            self.theme_menu.post(x, y)
            self._theme_menu_open = True
            try:
                self.theme_menu.focus_set()
            except Exception:
                pass
            self.root.after(10, self._release_menu_grab)
        except Exception:
            pass

    def _release_menu_grab(self):
        try:
            self.theme_menu.grab_release()
        except Exception:
            pass

    def _close_theme_menu(self):
        if not self._theme_menu_open:
            return
        try:
            self.theme_menu.unpost()
        except Exception:
            pass
        self._theme_menu_open = False

    def _maybe_close_theme_menu(self, event):
        if not self._theme_menu_open:
            return
        try:
            if event.widget == self.theme_btn:
                return
            if str(event.widget).startswith(str(self.theme_menu)):
                return
            self._close_theme_menu()
        except Exception:
            pass

    def _select_theme(self, name):
        self._close_theme_menu()
        self.apply_theme(name)

    def _refresh_theme_menu_checks(self):
        try:
            for i, tname in enumerate(THEME_ORDER):
                if tname == self.current_theme:
                    self.theme_menu.entryconfig(i, label=f"  {tname}")
                else:
                    self.theme_menu.entryconfig(i, label=f"    {tname}")
        except Exception:
            pass

    def _random_theme(self):
        self._close_theme_menu()
        options = [t for t in THEME_ORDER if t != self.current_theme]
        if options:
            self.apply_theme(random.choice(options))

    # ---------------- Shuffle ----------------
    def _next_shuffle_index(self):
        total = len(self.playlist)
        if total == 0:
            return None
        if len(self.shuffle_history) >= total:
            self.shuffle_history = []
            if total > 1 and self.current_index >= 0:
                self.shuffle_history.append(self.current_index)
        candidates = [i for i in range(total)
                      if i not in self.shuffle_history and i != self.current_index]
        if not candidates:
            return None
        return random.choice(candidates)

    def toggle_shuffle(self):
        self.shuffle_mode = not self.shuffle_mode
        if self.shuffle_mode:
            self.shuffle_history = [self.current_index] if self.current_index >= 0 else []
            self.status.config(text="Modo aleatorio ACTIVADO")
        else:
            self.shuffle_history = []
            self.status.config(text="Modo secuencial (por defecto)")
        self._refresh_shuffle_btn()

    def _refresh_shuffle_btn(self):
        if self._shuffle_btn is None:
            return
        if self.shuffle_mode:
            self._shuffle_btn.configure(bg=self.C("ACCENT"),
                                        activebackground=self.C("ACCENT_DARK"))
            color_key = "BG"
        else:
            self._shuffle_btn.configure(bg=self.C("BG_INPUT"),
                                        activebackground=self.C("ACCENT"))
            color_key = "ACCENT"
        icon = IconFactory.get("shuffle", 22, self.C(color_key))
        self._shuffle_btn.configure(image=icon)
        self._shuffle_btn.image = icon
        for i, (w, name, size, _) in enumerate(self._icon_widgets):
            if w is self._shuffle_btn:
                self._icon_widgets[i] = (w, name, size, color_key)
                break

    # ---------------- Sidebar ----------------
    def _refresh_playlists_sidebar(self):
        self.pl_listbox.delete(0, tk.END)
        for name in sorted(self.local_playlists.keys()):
            n = len(self.local_playlists[name])
            self.pl_listbox.insert(tk.END, f"{name}  ({n})")
        self.fav_btn.config(text=f"  Favoritos ({len(self.favorites)})")

    def _selected_playlist_name(self):
        sel = self.pl_listbox.curselection()
        if not sel:
            return None
        txt = self.pl_listbox.get(sel[0])
        name = txt.rsplit("  (", 1)[0]
        return name if name in self.local_playlists else None

    def _playlist_context_menu(self, event):
        idx = self.pl_listbox.nearest(event.y)
        if idx >= 0:
            self.pl_listbox.selection_clear(0, tk.END)
            self.pl_listbox.selection_set(idx)
        try:
            self.pl_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.pl_menu.grab_release()

    # ---------------- Favoritos ----------------
    def is_favorite(self, url):
        return any(f["url"] == url for f in self.favorites)

    def toggle_favorite_selected(self):
        sel = self.listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        if idx >= len(self.playlist):
            return
        item = self.playlist[idx]
        if item.get("type") == "playlist":
            messagebox.showinfo("Favoritos",
                                "Solo puedes guardar videos en favoritos.\n"
                                "Para playlists usa 'Guardar playlist completa...'.")
            return
        if self.is_favorite(item["url"]):
            self.favorites = [f for f in self.favorites if f["url"] != item["url"]]
            self.status.config(text=f"Quitado de favoritos: {item['title'][:40]}")
        else:
            self.favorites.append({
                "title": item["title"], "url": item["url"],
                "duration": item.get("duration", 0)})
            self.status.config(text=f"Anadido a favoritos: {item['title'][:40]}")
        self._save_data()
        self._refresh_playlists_sidebar()

    def show_favorites(self):
        if not self.favorites:
            messagebox.showinfo("Favoritos", "Aun no tienes favoritos.")
            return
        self.current_query = ""
        self.current_sp = ""
        self.loaded_count = 0
        self.playlist = []
        self.listbox.delete(0, tk.END)
        self.shuffle_history = []
        for f in self.favorites:
            duration = f.get("duration", 0)
            mins, secs = divmod(int(duration), 60)
            label = f"{f['title']}  [{mins:02d}:{secs:02d}]"
            self.playlist.append({"title": f["title"], "url": f["url"],
                                  "type": "video", "duration": duration})
            self.listbox.insert(tk.END, label)
        self.load_more_btn.config(state="disabled")
        self.status.config(text=f"{len(self.favorites)} favoritos")

    # ---------------- Playlists locales ----------------
    def create_playlist(self):
        name = simpledialog.askstring("Nueva playlist", "Nombre de la playlist:",
                                      parent=self.root)
        if not name:
            return
        name = name.strip()
        if not name:
            return
        if name in self.local_playlists:
            messagebox.showwarning("Ya existe", "Ya tienes una playlist con ese nombre.")
            return
        self.local_playlists[name] = []
        self._save_data()
        self._refresh_playlists_sidebar()
        self.status.config(text=f"Playlist '{name}' creada")

    def open_local_playlist(self):
        name = self._selected_playlist_name()
        if not name:
            return
        items = self.local_playlists.get(name, [])
        if not items:
            messagebox.showinfo("Playlist vacia", "Esta playlist esta vacia.")
            return
        self.current_query = ""
        self.current_sp = ""
        self.loaded_count = 0
        self.playlist = []
        self.listbox.delete(0, tk.END)
        self.shuffle_history = []
        for it in items:
            duration = it.get("duration", 0)
            mins, secs = divmod(int(duration), 60)
            label = f"{it['title']}  [{mins:02d}:{secs:02d}]"
            self.playlist.append({"title": it["title"], "url": it["url"],
                                  "type": "video", "duration": duration})
            self.listbox.insert(tk.END, label)
        self.load_more_btn.config(state="disabled")
        self.status.config(text=f"Playlist '{name}' - {len(items)} canciones")

    def rename_playlist(self):
        name = self._selected_playlist_name()
        if not name:
            return
        new = simpledialog.askstring("Renombrar", "Nuevo nombre:", initialvalue=name,
                                     parent=self.root)
        if not new or new == name:
            return
        new = new.strip()
        if new in self.local_playlists:
            messagebox.showwarning("Ya existe", "Ya hay una playlist con ese nombre.")
            return
        new_dict = {}
        for k, v in self.local_playlists.items():
            if k == name:
                new_dict[new] = v
            else:
                new_dict[k] = v
        self.local_playlists = new_dict
        self._save_data()
        self._refresh_playlists_sidebar()

    def delete_playlist(self):
        name = self._selected_playlist_name()
        if not name:
            return
        if not messagebox.askyesno("Eliminar", f"Eliminar la playlist '{name}'?"):
            return
        del self.local_playlists[name]
        self._save_data()
        self._refresh_playlists_sidebar()
        self.status.config(text=f"Playlist '{name}' eliminada")

    def add_selected_to_local_playlist(self):
        sel = self.listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        if idx >= len(self.playlist):
            return
        item = self.playlist[idx]
        if item.get("type") == "playlist":
            messagebox.showinfo("Aviso",
                                "Para playlists de YouTube usa 'Guardar playlist completa...'.")
            return
        names = sorted(self.local_playlists.keys())
        if not names:
            if messagebox.askyesno("Sin playlists",
                                   "No tienes playlists locales. Crear una ahora?"):
                self.create_playlist()
            return

        win = tk.Toplevel(self.root)
        win.title("Anadir a playlist")
        win.configure(bg=self.C("BG"))
        win.geometry("320x340")
        win.transient(self.root)
        win.grab_set()

        tk.Label(win, text="Elige una playlist:", fg=self.C("FG"), bg=self.C("BG"),
                 font=("Segoe UI", 11)).pack(pady=8)

        lb = tk.Listbox(win, bg=self.C("BG_INPUT"), fg=self.C("FG"), relief="flat",
                        selectbackground=self.C("SELECT_BG"),
                        selectforeground=self.C("SELECT_FG"),
                        font=("Segoe UI", 10), activestyle="none",
                        highlightthickness=1,
                        highlightbackground=self.C("ACCENT_DARK"))
        lb.pack(fill="both", expand=True, padx=10, pady=6)
        for n in names:
            lb.insert(tk.END, f"{n}  ({len(self.local_playlists[n])})")

        def confirm():
            s = lb.curselection()
            if not s:
                return
            chosen = names[s[0]]
            if self.is_duplicate_in_playlist(chosen, item["url"]):
                if not messagebox.askyesno("Duplicado",
                                           "Esa cancion ya esta en la playlist. Anadir igual?"):
                    return
            self.local_playlists[chosen].append({
                "title": item["title"], "url": item["url"],
                "duration": item.get("duration", 0)})
            self._save_data()
            self._refresh_playlists_sidebar()
            self.status.config(text=f"Anadido a '{chosen}'")
            win.destroy()

        tk.Button(win, text="Anadir", command=confirm,
                  bg=self.C("ACCENT"), fg=self.C("BG"), relief="flat",
                  activebackground=self.C("ACCENT_DARK"),
                  activeforeground=self.C("BG"),
                  font=("Segoe UI", 10, "bold"),
                  padx=14, pady=4, bd=0).pack(pady=8)

    def is_duplicate_in_playlist(self, name, url):
        return any(x["url"] == url for x in self.local_playlists.get(name, []))

    def save_playlist_as_local(self):
        sel = self.listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        if idx >= len(self.playlist):
            return
        item = self.playlist[idx]
        if item.get("type") != "playlist":
            messagebox.showinfo("Aviso", "Selecciona una playlist de YouTube.")
            return
        name = simpledialog.askstring("Guardar playlist",
                                      "Nombre para tu playlist local:",
                                      initialvalue=item["title"][:60],
                                      parent=self.root)
        if not name:
            return
        name = name.strip()
        if not name:
            return
        if name in self.local_playlists:
            if not messagebox.askyesno("Ya existe",
                                       f"Ya existe '{name}'. Sobrescribir?"):
                return

        self.status.config(text=f"Guardando playlist '{name}'...")

        def worker():
            try:
                ydl_opts = {"quiet": True, "no_warnings": True,
                            "extract_flat": True, "skip_download": True}
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(item["url"], download=False)
                    entries = info.get("entries", []) or []
                saved = []
                for e in entries:
                    if not e:
                        continue
                    url = e.get("url") or f"https://www.youtube.com/watch?v={e.get('id')}"
                    saved.append({
                        "title": e.get("title", "Desconocido"),
                        "url": url,
                        "duration": int(e.get("duration") or 0)})
                if not saved:
                    self.root.after(0, lambda: self.status.config(
                        text="La playlist esta vacia o no es accesible."))
                    return
                self.local_playlists[name] = saved
                self._save_data()
                self.root.after(0, lambda: self._refresh_playlists_sidebar())
                self.root.after(0, lambda: self.status.config(
                    text=f"Playlist '{name}' guardada con {len(saved)} canciones"))
            except Exception as e:
                self.root.after(0, lambda: self.status.config(
                    text=f"Error guardando playlist: {e}"))

        threading.Thread(target=worker, daemon=True).start()

    # ---------------- Context menu listbox ----------------
    def _listbox_context_menu(self, event):
        idx = self.listbox.nearest(event.y)
        if idx >= 0:
            self.listbox.selection_clear(0, tk.END)
            self.listbox.selection_set(idx)
        if 0 <= idx < len(self.playlist):
            is_pl = self.playlist[idx].get("type") == "playlist"
            if is_pl:
                self.lb_menu.entryconfig("Guardar playlist completa...", state="normal")
                self.lb_menu.entryconfig("Anadir/Quitar favorito", state="disabled")
                self.lb_menu.entryconfig("Anadir a playlist local...", state="disabled")
            else:
                self.lb_menu.entryconfig("Guardar playlist completa...", state="disabled")
                self.lb_menu.entryconfig("Anadir/Quitar favorito", state="normal")
                self.lb_menu.entryconfig("Anadir a playlist local...", state="normal")
        try:
            self.lb_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.lb_menu.grab_release()

    # ---------------- Búsqueda ----------------
    def _get_filter_sp(self):
        t = self.search_type.get()
        if t in ("Canciones", "Videos"):
            return YT_FILTER_SONGS
        elif t == "Playlists":
            return YT_FILTER_PLAYLISTS
        return YT_FILTER_ALL

    def search(self):
        query = self.search_entry.get().strip()
        if not query:
            messagebox.showwarning("Aviso", "Escribe algo para buscar.")
            return
        self.current_query = query
        self.current_sp = self._get_filter_sp()
        self.loaded_count = 0
        self.playlist.clear()
        self.listbox.delete(0, tk.END)
        self.shuffle_history = []
        self.load_more_btn.config(state="disabled")
        self.status.config(text="Buscando...")
        self._fetch_page()

    def load_more(self):
        if self.loading or not self.current_query:
            return
        self.load_more_btn.config(state="disabled")
        self.status.config(text="Cargando mas resultados...")
        self._fetch_page()

    def _fetch_page(self):
        if self.loading:
            return
        self.loading = True
        threading.Thread(
            target=self._search_thread,
            args=(self.current_query, self.current_sp, self.loaded_count),
            daemon=True,
        ).start()

    def _search_thread(self, query, sp, start_index):
        try:
            search_url = (f"https://www.youtube.com/results?"
                          f"search_query={query.replace(' ', '+')}")
            if sp:
                search_url += f"&sp={sp}"
            ydl_opts = {
                "quiet": True, "no_warnings": True,
                "extract_flat": True, "skip_download": True,
                "playliststart": start_index + 1,
                "playlistend": start_index + PAGE_SIZE,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(search_url, download=False)
                entries = info.get("entries", []) or []
            if not entries:
                self.root.after(0, lambda: self._on_page_loaded(0, False))
                return
            playlist_jobs = []
            new_items = 0
            for entry in entries:
                if not entry:
                    continue
                is_playlist = (
                    entry.get("_type") == "playlist"
                    or entry.get("ie_key") == "YoutubeTab"
                    or entry.get("playlist_count") is not None
                )
                title = entry.get("title", "Desconocido")
                url = entry.get("url") or entry.get("webpage_url") or ""
                if url and not url.startswith("http"):
                    url = f"https://www.youtube.com/watch?v={url}"
                duration = entry.get("duration") or 0
                mins, secs = divmod(int(duration), 60)
                if is_playlist:
                    count = entry.get("playlist_count") or entry.get("n_entries") or 0
                    count_txt = str(count) if count else "..."
                    label = f"[Playlist - {count_txt}] {title}"
                    item = {"title": title, "url": url, "type": "playlist",
                            "count": count}
                    idx = len(self.playlist)
                    self.playlist.append(item)
                    self.root.after(0, lambda l=label: self.listbox.insert(tk.END, l))
                    if not count:
                        playlist_jobs.append((idx, url))
                else:
                    label = f"{title}  [{mins:02d}:{secs:02d}]"
                    item = {"title": title, "url": url, "type": "video",
                            "duration": int(duration)}
                    self.playlist.append(item)
                    self.root.after(0, lambda l=label: self.listbox.insert(tk.END, l))
                new_items += 1
            self.loaded_count = len(self.playlist)
            for idx, url in playlist_jobs:
                threading.Thread(target=self._count_playlist,
                                 args=(idx, url), daemon=True).start()
            has_more = new_items >= PAGE_SIZE
            self.root.after(0, lambda: self._on_page_loaded(new_items, has_more))
        except Exception as e:
            self.root.after(0, lambda: self._on_page_error(str(e)))

    def _on_page_loaded(self, new_items, has_more):
        self.loading = False
        total = len(self.playlist)
        if new_items == 0:
            self.status.config(text=f"No hay mas resultados. Total: {total}")
            self.load_more_btn.config(state="disabled")
        else:
            self.status.config(text=f"{new_items} nuevos - total {total}")
            self.load_more_btn.config(state="normal" if has_more else "disabled")

    def _on_page_error(self, msg):
        self.loading = False
        self.status.config(text=f"Error: {msg}")
        self.load_more_btn.config(state="normal")

    def _count_playlist(self, index, url):
        try:
            ydl_opts = {"quiet": True, "no_warnings": True,
                        "extract_flat": True, "skip_download": True,
                        "playlistend": 1}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
            count = (info.get("playlist_count") or info.get("n_entries")
                     or len(info.get("entries") or []) or 0)
            if count and 0 <= index < len(self.playlist):
                self.playlist[index]["count"] = count
                title = self.playlist[index]["title"]
                new_label = f"[Playlist - {count}] {title}"
                self.root.after(0, lambda: self._update_listbox_item(index, new_label))
        except Exception:
            pass

    def _update_listbox_item(self, index, text):
        if not (0 <= index < self.listbox.size()):
            return
        selected = list(self.listbox.curselection())
        self.listbox.delete(index)
        self.listbox.insert(index, text)
        for i in selected:
            self.listbox.selection_set(i)

    # ---------------- Reproducción ----------------
    def play_selected(self):
        sel = self.listbox.curselection()
        if not sel:
            return
        self.current_index = sel[0]
        self._play_index()

    def _play_index(self):
        if not (0 <= self.current_index < len(self.playlist)):
            return
        song = self.playlist[self.current_index]
        if song.get("type") == "playlist":
            self.status.config(text=f"Cargando playlist: {song['title'][:40]}...")
            self.now_playing.config(text=f"  Playlist: {song['title'][:70]}")
            threading.Thread(target=self._expand_playlist,
                             args=(song,), daemon=True).start()
            return
        self.now_playing.config(text=f"  {song['title'][:80]}")
        self.status.config(text="Obteniendo URL de streaming...")
        threading.Thread(target=self._stream_thread, args=(song,), daemon=True).start()

    def _expand_playlist(self, playlist_item):
        try:
            ydl_opts = {"quiet": True, "no_warnings": True,
                        "extract_flat": True, "skip_download": True}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(playlist_item["url"], download=False)
                entries = info.get("entries", [])
            added = 0
            for entry in entries:
                if not entry:
                    continue
                title = entry.get("title", "Desconocido")
                url = entry.get("url") or f"https://www.youtube.com/watch?v={entry.get('id')}"
                duration = entry.get("duration") or 0
                mins, secs = divmod(int(duration), 60)
                new_item = {"title": title, "url": url, "type": "video",
                            "duration": int(duration)}
                self.playlist.append(new_item)
                label = f"{title}  [{mins:02d}:{secs:02d}]"
                self.root.after(0, lambda l=label: self.listbox.insert(tk.END, l))
                added += 1
            if added > 0:
                first_new = len(self.playlist) - added
                self.current_index = first_new
                self.root.after(0, lambda: self.listbox.selection_clear(0, tk.END))
                self.root.after(0, lambda i=first_new: self.listbox.selection_set(i))
                self.root.after(0, lambda i=first_new: self.listbox.see(i))
                self.root.after(0, lambda: self.status.config(
                    text=f"Playlist cargada ({added} videos). Reproduciendo..."))
                self._play_index()
            else:
                self.root.after(0, lambda: self.status.config(
                    text="Playlist vacia o inaccesible."))
        except Exception as e:
            self.root.after(0, lambda: self.status.config(text=f"Error playlist: {e}"))

    def _stream_thread(self, song):
        try:
            ydl_opts = {"format": "bestaudio/best", "quiet": True, "no_warnings": True}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(song["url"], download=False)
                stream_url = info.get("url")
                if not stream_url:
                    formats = info.get("formats", [])
                    audio_formats = [f for f in formats if f.get("vcodec") == "none"]
                    if audio_formats:
                        stream_url = audio_formats[-1]["url"]
            if not stream_url:
                raise Exception("No se pudo obtener la URL del stream")

            self._ended = False
            self._last_duration = 0.0
            self._buffering = False
            self._idle_strikes = 0
            self._starting = True
            self._started_at = time.time()
            self._seeking = False
            self._seek_value = 0.0

            try:
                self.player.command("set_property", "eof-reached", False)
            except Exception:
                pass

            self.player.play(stream_url)
            self.player.pause = False
            self.is_paused = False

            pause_icon = IconFactory.get("pause", 26, self.C("BG"))
            self._icon_pause = pause_icon
            self.root.after(0, lambda: self.play_btn.config(image=pause_icon))
            self.root.after(0, lambda: self.status.config(text="Cargando..."))
        except Exception as e:
            self.root.after(0, lambda: self.status.config(text=f"Error: {e}"))

    def _on_track_end(self):
        if self._ended or self._starting:
            return
        self._ended = True
        self.root.after(300, self._advance_after_end)

    def _advance_after_end(self):
        if self.current_index < 0:
            return
        try:
            busy = self.player.core_idle is False
        except Exception:
            busy = False
        if busy:
            self._ended = False
            return

        if self.shuffle_mode:
            idx = self._next_shuffle_index()
            if idx is not None:
                self.shuffle_history.append(idx)
                self.current_index = idx
                self.listbox.selection_clear(0, tk.END)
                self.listbox.selection_set(idx)
                self.listbox.see(idx)
                self._play_index()
                return

        if self.current_index + 1 < len(self.playlist):
            self.next_song()
        else:
            self.status.config(text="Fin de la lista")

    # ---------------- Controles ----------------
    def toggle_play(self):
        if self.current_index < 0:
            self.play_selected()
            return
        if self.player.pause:
            self.player.pause = False
            self.is_paused = False
            icon = IconFactory.get("pause", 26, self.C("BG"))
            self._icon_pause = icon
            self.play_btn.config(image=icon)
            self.status.config(text="Reproduciendo (streaming)")
        else:
            self.player.pause = True
            self.is_paused = True
            icon = IconFactory.get("play", 26, self.C("BG"))
            self._icon_play = icon
            self.play_btn.config(image=icon)
            self.status.config(text="Pausado")

    def stop_song(self):
        self._ended = True
        self._starting = False
        self.player.stop()
        self.is_paused = False
        self._last_duration = 0.0
        self._buffering = False
        self._idle_strikes = 0
        self._seeking = False
        self._seek_value = 0.0
        icon = IconFactory.get("play", 26, self.C("BG"))
        self._icon_play = icon
        self.play_btn.config(image=icon)
        self.time_label.config(text="00:00 / 00:00")
        self._draw_progress()
        self.status.config(text="Detenido")

    def next_song(self):
        if self.current_index + 1 < len(self.playlist):
            self.current_index += 1
            self.listbox.selection_clear(0, tk.END)
            self.listbox.selection_set(self.current_index)
            self.listbox.see(self.current_index)
            self._play_index()

    def prev_song(self):
        if self.current_index - 1 >= 0:
            self.current_index -= 1
            self.listbox.selection_clear(0, tk.END)
            self.listbox.selection_set(self.current_index)
            self.listbox.see(self.current_index)
            self._play_index()

    def _on_volume(self, value):
        try:
            self.player.volume = float(value)
        except Exception:
            pass

    # ---------------- Progreso ----------------
    def _on_progress_press(self, event):
        if self._last_duration <= 0:
            return
        self._seeking = True
        self._update_seek_from_x(event.x)

    def _on_progress_drag(self, event):
        if self._seeking:
            self._update_seek_from_x(event.x)

    def _on_progress_release(self, event):
        if not self._seeking:
            return
        self._update_seek_from_x(event.x)
        self._seeking = False
        try:
            if self._seek_value > 0:
                self.player.time_pos = self._seek_value
        except Exception:
            pass

    def _update_seek_from_x(self, x):
        try:
            w = self.progress_canvas.winfo_width()
            if w <= 0 or self._last_duration <= 0:
                return
            ratio = max(0.0, min(1.0, x / w))
            self._seek_value = ratio * self._last_duration
            self._draw_progress(preview_ratio=ratio)
            self.time_label.config(
                text=f"{self._fmt(self._seek_value)} / {self._fmt(self._last_duration)}")
        except Exception:
            pass

    def _draw_progress(self, preview_ratio=None):
        try:
            c = self.progress_canvas
            w = c.winfo_width()
            h = c.winfo_height()
            if w <= 1 or h <= 1:
                return

            c.delete("all")
            radius = h // 2

            def rounded_bar(x0, x1, color):
                if x1 - x0 < 1:
                    return
                c.create_rectangle(x0 + radius, 2, x1 - radius, h - 2,
                                   fill=color, outline=color)
                c.create_oval(x0, 2, x0 + 2 * radius, h - 2,
                              fill=color, outline=color)
                c.create_oval(x1 - 2 * radius, 2, x1, h - 2,
                              fill=color, outline=color)

            rounded_bar(0, w, self.C("BG_INPUT"))

            dur = self._last_duration
            buf_end_ratio = 0.0
            if dur > 0:
                try:
                    cache = self.player.demuxer_cache_time
                    if not cache:
                        cache = self.player.demuxer_cache_duration
                    if cache is None:
                        cache = 0
                except Exception:
                    cache = 0
                try:
                    pos = self.player.time_pos or 0
                except Exception:
                    pos = 0
                buf_end = pos + (cache or 0)
                buf_end_ratio = max(0.0, min(1.0, buf_end / dur))
            if buf_end_ratio > 0:
                rounded_bar(0, int(w * buf_end_ratio), self.C("ACCENT_DARK"))

            if preview_ratio is not None:
                prog_ratio = preview_ratio
            else:
                try:
                    pos = self.player.time_pos or 0
                except Exception:
                    pos = 0
                prog_ratio = (pos / dur) if dur > 0 else 0.0
                prog_ratio = max(0.0, min(1.0, prog_ratio))
            if prog_ratio > 0:
                rounded_bar(0, int(w * prog_ratio), self.C("ACCENT"))

            marker_ratio = preview_ratio if preview_ratio is not None else prog_ratio
            mx = int(w * marker_ratio)
            c.create_oval(mx - radius + 1, 2, mx + radius - 1, h - 2,
                          fill=self.C("FG"), outline=self.C("ACCENT"), width=2)
        except Exception:
            pass

    def _update_progress(self):
        try:
            if self.current_index >= 0:
                try:
                    dur_now = self.player.duration
                except Exception:
                    dur_now = None
                if dur_now and dur_now > 0:
                    self._last_duration = float(dur_now)
                dur = self._last_duration

                if self._starting:
                    try:
                        pos_chk = self.player.time_pos
                    except Exception:
                        pos_chk = None
                    try:
                        idle_chk = bool(self.player.core_idle)
                    except Exception:
                        idle_chk = True

                    elapsed = time.time() - self._started_at
                    started = False
                    if pos_chk is not None and pos_chk > 0.3:
                        started = True
                    elif not idle_chk:
                        started = True
                    elif elapsed > 8.0:
                        started = True

                    if started:
                        self._starting = False
                        self._idle_strikes = 0
                        self.status.config(text="Reproduciendo (streaming)")

                if self._starting:
                    self.root.after(500, self._update_progress)
                    return

                try:
                    buffering = bool(self.player.paused_for_cache) or bool(self.player.core_idle)
                except Exception:
                    buffering = False
                if buffering and not self.is_paused:
                    if not self._buffering:
                        self._buffering = True
                        self.status.config(text="Buffering...")
                else:
                    if self._buffering:
                        self._buffering = False
                        self.status.config(text="Reproduciendo (streaming)")

                if not self._seeking:
                    try:
                        pos = self.player.time_pos or 0
                    except Exception:
                        pos = 0
                    if dur > 0:
                        self.time_label.config(
                            text=f"{self._fmt(pos)} / {self._fmt(dur)}")
                    self._draw_progress()

                if (not self.is_paused
                        and not self._ended
                        and not self._buffering
                        and not self._starting):
                    try:
                        idle = bool(self.player.core_idle)
                    except Exception:
                        idle = False
                    if idle:
                        self._idle_strikes += 1
                        if self._idle_strikes >= 4:
                            self._idle_strikes = 0
                            self._on_track_end()
                    else:
                        self._idle_strikes = 0
        except Exception:
            pass
        self.root.after(500, self._update_progress)

    @staticmethod
    def _fmt(seconds):
        seconds = int(seconds)
        m, s = divmod(seconds, 60)
        return f"{m:02d}:{s:02d}"

    def on_close(self):
        try:
            self._save_data()
            self._save_theme_setting()
        except Exception:
            pass
        try:
            self.player.terminate()
        except Exception:
            pass
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = YouTubeMusicPlayer(root)
    root.mainloop()
