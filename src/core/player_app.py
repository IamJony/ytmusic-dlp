import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
import threading
import json
import os
import re
import random
import time
import webbrowser
from collections import OrderedDict

import yt_dlp
import mpv

from src.utils.constants import (
    YT_FILTER_ALL, YT_FILTER_SONGS, YT_FILTER_PLAYLISTS,
    PAGE_SIZE, DATA_FILE, SETTINGS_FILE, DOWNLOAD_DIR, GITHUB_URL,
    APP_VERSION, STREAM_CACHE_TTL, STREAM_CACHE_MAX
)
from src.utils.helpers import notify, fmt_time, blend
from src.ui.icons import IconFactory, create_youtube_icon
from src.ui.reorderable_listbox import ReorderableListbox
from src.ui.feedback import Toast, Spinner
from src.ui.styles import (
    FONT_TITLE, FONT_SUBTITLE, FONT_BODY, FONT_BODY_B, FONT_SMALL,
    FONT_TINY, FONT_TIME, PAD_XS, PAD_S, PAD_M, PAD_L, PAD_XL
)
from src.data.themes import THEMES, THEME_ORDER

DOWNLOADS_PLAYLIST_NAME = "Descargas"


class YouTubeMusicPlayer:
    def __init__(self, root):
        self.root = root
        self.root.title("ytmusic-dlp  ·  by IamJony")
        self.root.geometry("1100x800")
        self.root.minsize(900, 640)
        self.root.configure(bg="#0a0e14")

        try:
            self._window_icon = create_youtube_icon(64)
            self.root.iconphoto(True, self._window_icon)
        except Exception:
            pass

        self._closing = False
        self._progress_job = None
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
        self._repeat_mode = 0

        self.current_query = ""
        self.current_sp = ""
        self.loaded_count = 0
        self.loading = False

        self._themed_widgets = []
        self._hover_widgets = []
        self._icon_widgets = []
        self._theme_menu_open = False
        self._open_menu = None

        self._stream_cache = OrderedDict()
        self._current_playing_row = -1
        self._notified_current = False

        self._search_lock = threading.Lock()
        self._end_lock = threading.Lock()

        self.player = mpv.MPV(
            ytdl=False, video=False, really_quiet=True,
            input_default_bindings=False, input_vo_keyboard=False,
            cache=False, network_timeout=5,
        )
        self._ended = False
        self._last_duration = 0.0
        self._buffering = False
        self._idle_strikes = 0
        self._starting = False
        self._started_at = 0.0
        self._seeking = False
        self._seek_value = 0.0
        self._seek_guard_until = 0.0
        self._hover_progress = False

        @self.player.property_observer('eof-reached')
        def _on_eof(_n, v):
            if self._closing:
                return
            if v and not self._starting and time.time() >= self._seek_guard_until:
                self.root.after(150, self._on_track_end)

        @self.player.property_observer('core-idle')
        def _on_idle(_n, v):
            if self._closing:
                return
            if (v and not self._starting
                    and self.current_index >= 0
                    and not self.is_paused
                    and not self._seeking
                    and time.time() >= self._seek_guard_until):
                self.root.after(150, self._on_track_end)

        self._build_ui()
        self.toast = Toast(self.root, self.C)
        self.spinner = Spinner(self.root, self.status)
        self.apply_theme(self.current_theme, save=False)

        self.root.bind("<Button-1>", self._maybe_close_menus_click, add="+")
        self.root.bind("<Button-3>", self._maybe_close_menus_click, add="+")
        self.root.bind("<Escape>", lambda e: self._close_context_menus(), add="+")
        self.root.bind("<Button-1>", self._maybe_close_theme_menu, add="+")
        self.root.bind("<FocusOut>", lambda e: self._close_theme_menu(), add="+")

        self._bind_shortcuts()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def _bind_shortcuts(self):
        self.root.bind("<space>", self._shortcut_play)
        self.root.bind("<Control-Right>", lambda e: self.next_song())
        self.root.bind("<Control-Left>", lambda e: self.prev_song())
        self.root.bind("<Control-f>", lambda e: self.search_entry.focus_set())
        self.root.bind("<Escape>", lambda e: self.stop_song())
        self.root.bind("<Control-s>", lambda e: self.toggle_shuffle())
        self.root.bind("<Control-r>", lambda e: self._cycle_repeat())

    def _shortcut_play(self, event):
        if self.root.focus_get() is self.search_entry:
            return
        self.toggle_play()

    def _bind_hover(self, widget, normal_key, hover_key):
        def on_enter(_):
            try:
                widget.configure(bg=self.C(hover_key))
            except Exception:
                pass
        def on_leave(_):
            try:
                widget.configure(bg=self.C(normal_key))
            except Exception:
                pass
        widget.bind("<Enter>", on_enter, add="+")
        widget.bind("<Leave>", on_leave, add="+")
        self._hover_widgets.append((widget, normal_key, hover_key))

    def _apply_hover_colors(self):
        for widget, normal_key, _ in self._hover_widgets:
            try:
                widget.configure(bg=self.C(normal_key))
            except Exception:
                pass

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

    def _load_data(self):
        try:
            if os.path.exists(DATA_FILE):
                with open(DATA_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.favorites = data.get("favorites", [])
                    self.local_playlists = data.get("local_playlists", {})
        except Exception as e:
            print(f"No se pudo cargar datos: {e}")
        self._refresh_downloads_playlist()

    def _save_data(self):
        try:
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                playlists_to_save = {
                    k: v for k, v in self.local_playlists.items()
                    if k != DOWNLOADS_PLAYLIST_NAME
                }
                json.dump({
                    "favorites": self.favorites,
                    "local_playlists": playlists_to_save,
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"No se pudo guardar datos: {e}")

    def C(self, key):
        return self.colors.get(key, "#ffffff")

    def _register(self, widget, hover=None, **color_map):
        self._themed_widgets.append((widget, color_map))
        if hover:
            self._bind_hover(widget, hover[0], hover[1])
        return widget

    def apply_theme(self, name, save=True):
        if name not in THEMES:
            return
        self.current_theme = name
        self.colors = THEMES[name]
        if save:
            self._save_theme_setting()

        self.root.configure(bg=self.C("BG"))

        for widget, mapping in self._themed_widgets:
            try:
                widget.configure(**{opt: self.C(key) for opt, key in mapping.items()})
            except Exception:
                pass

        self._apply_hover_colors()

        for widget, icon_name, size, color_key in self._icon_widgets:
            try:
                icon = IconFactory.get(icon_name, size, self.C(color_key))
                widget.configure(image=icon)
                widget.image = icon
            except Exception:
                pass

        self._build_pl_menu()
        self._build_lb_menu()

        try:
            self.theme_menu.configure(
                bg=self.C("BG_PANEL"), fg=self.C("FG"),
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
        self._refresh_repeat_btn()

        try:
            self.header_canvas.configure(bg=self.C("BG_PANEL"))
            self._draw_header_gradient()
        except Exception:
            pass

        try:
            self.progress_canvas.configure(bg=self.C("BG"))
            self._draw_progress()
        except Exception:
            pass

        style = ttk.Style()
        style.theme_use("clam")
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

        self._refresh_all_listbox_colors()
        self._update_empty_state()
        try:
            self.status.config(text=f"Tema: {name}")
        except Exception:
            pass

    def _draw_header_gradient(self):
        try:
            c = self.header_canvas
            c.delete("all")
            w = c.winfo_width() or 1100
            h = c.winfo_height() or 56
            c1, c2 = self.C("BG_PANEL"), self.C("BG")
            for i in range(h):
                color = blend(c1, c2, i / max(1, h - 1))
                c.create_line(0, i, w, i, fill=color)
        except Exception:
            pass

    def _build_ui(self):
        style = ttk.Style()
        style.theme_use("clam")

        self.header_canvas = tk.Canvas(self.root, height=56,
                                        bg=self.C("BG_PANEL"),
                                        highlightthickness=0, bd=0)
        self.header_canvas.pack(fill="x")
        self._register(self.header_canvas, bg="BG_PANEL")
        self.header_canvas.bind("<Configure>", lambda e: self._draw_header_gradient())

        header_inner = tk.Frame(self.header_canvas, bg=self.C("BG_PANEL"))
        self._register(header_inner, bg="BG_PANEL")
        header_inner.place(x=0, y=0, relwidth=1, relheight=1)

        if hasattr(self, "_window_icon"):
            logo = tk.Label(header_inner, image=self._window_icon,
                            bg=self.C("BG_PANEL"))
            logo.image = self._window_icon
            logo.pack(side="left", padx=(PAD_M, PAD_S))
            self._register(logo, bg="BG_PANEL")

        title = tk.Label(header_inner, text="ytmusic-dlp",
                         font=FONT_TITLE, fg=self.C("FG"),
                         bg=self.C("BG_PANEL"))
        title.pack(side="left")
        self._register(title, fg="FG", bg="BG_PANEL")

        version = tk.Label(header_inner, text=f"v{APP_VERSION}",
                           font=FONT_TINY, fg=self.C("FG_DIM"),
                           bg=self.C("BG_PANEL"))
        version.pack(side="left", padx=(PAD_S, 0), pady=(4, 0))
        self._register(version, fg="FG_DIM", bg="BG_PANEL")

        def make_icon_btn(parent, icon_name, text, cmd, color_key="ACCENT",
                          bg_key="BG_PANEL", size=16):
            icon = IconFactory.get(icon_name, size, self.C(color_key))
            b = tk.Button(parent, text=f"  {text}", image=icon, compound="left",
                          command=cmd, bg=self.C(bg_key), fg=self.C(color_key),
                          relief="flat",
                          activebackground=self.C("BG_INPUT"),
                          activeforeground=self.C(color_key),
                          font=FONT_SMALL, padx=PAD_M, bd=0)
            b.image = icon
            self._register(b, bg=bg_key, fg=color_key,
                           activebackground="BG_INPUT",
                           activeforeground=color_key,
                           hover=(bg_key, "BG_INPUT"))
            self._icon_widgets.append((b, icon_name, size, color_key))
            return b

        btns_right = tk.Frame(header_inner, bg=self.C("BG_PANEL"))
        btns_right.pack(side="right", padx=PAD_M)
        self._register(btns_right, bg="BG_PANEL")

        make_icon_btn(btns_right, "upload", "Exportar",
                      self.export_data).pack(side="left", padx=PAD_XS)
        make_icon_btn(btns_right, "download", "Importar",
                      self.import_data).pack(side="left", padx=PAD_XS)

        palette_icon = IconFactory.get("palette", 15, self.C("ACCENT"))
        self.theme_btn = tk.Button(
            btns_right,
            text=f"  Tema: {self.current_theme}",
            image=palette_icon, compound="left",
            command=self._open_theme_menu,
            bg=self.C("BG_PANEL"), fg=self.C("ACCENT"),
            relief="flat",
            activebackground=self.C("BG_INPUT"),
            activeforeground=self.C("ACCENT"),
            font=FONT_SMALL, padx=PAD_M, bd=0)
        self.theme_btn.image = palette_icon
        self.theme_btn.pack(side="left", padx=PAD_XS)
        self._register(self.theme_btn, bg="BG_PANEL", fg="ACCENT",
                       activebackground="BG_INPUT", activeforeground="ACCENT",
                       hover=("BG_PANEL", "BG_INPUT"))

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

        accent_line = tk.Frame(self.root, bg=self.C("ACCENT"), height=2)
        accent_line.pack(fill="x")
        self._register(accent_line, bg="ACCENT")

        search_frame = tk.Frame(self.root, bg=self.C("BG"))
        search_frame.pack(fill="x", padx=PAD_L, pady=PAD_M)
        self._register(search_frame, bg="BG")

        lbl = tk.Label(search_frame, text="Buscar:", fg=self.C("FG"), bg=self.C("BG"),
                       font=FONT_BODY)
        lbl.pack(side="left")
        self._register(lbl, fg="FG", bg="BG")

        self.search_entry = tk.Entry(search_frame, font=FONT_BODY,
                                     bg=self.C("BG_INPUT"), fg=self.C("FG"),
                                     insertbackground=self.C("ACCENT"),
                                     relief="flat", highlightthickness=1,
                                     highlightbackground=self.C("ACCENT_DARK"),
                                     highlightcolor=self.C("ACCENT_HOVER"))
        self.search_entry.pack(side="left", fill="x", expand=True,
                               padx=PAD_S, ipady=6)
        self.search_entry.bind("<Return>", lambda e: self.search())
        self._register(self.search_entry, bg="BG_INPUT", fg="FG",
                       insertbackground="ACCENT",
                       highlightbackground="ACCENT_DARK",
                       highlightcolor="ACCENT")

        self.search_type = tk.StringVar(value="Todo")
        type_menu = ttk.Combobox(search_frame, textvariable=self.search_type,
                                 values=["Todo", "Canciones", "Videos", "Playlists"],
                                 state="readonly", width=11, font=FONT_SMALL,
                                 style="AW.TCombobox")
        type_menu.pack(side="left", padx=(0, PAD_S))

        search_icon = IconFactory.get("search", 14, self.C("BG"))
        sb = tk.Button(search_frame, text="  Buscar", image=search_icon,
                       compound="left",
                       command=self.search, bg=self.C("ACCENT"), fg=self.C("BG"),
                       relief="flat", activebackground=self.C("ACCENT_DARK"),
                       activeforeground=self.C("BG"),
                       font=FONT_BODY_B, padx=PAD_M, bd=0)
        sb.image = search_icon
        sb.pack(side="left")
        self._register(sb, bg="ACCENT", fg="BG",
                       activebackground="ACCENT_DARK", activeforeground="BG",
                       hover=("ACCENT", "ACCENT_HOVER"))
        self._icon_widgets.append((sb, "search", 14, "BG"))

        body = tk.Frame(self.root, bg=self.C("BG"))
        body.pack(fill="both", expand=True, padx=PAD_L, pady=PAD_S)
        self._register(body, bg="BG")

        sidebar = tk.Frame(body, bg=self.C("BG_PANEL"), width=260,
                           highlightthickness=1,
                           highlightbackground=self.C("ACCENT_DARK"))
        sidebar.pack(side="left", fill="y", padx=(0, PAD_S))
        sidebar.pack_propagate(False)
        self._register(sidebar, bg="BG_PANEL", highlightbackground="ACCENT_DARK")

        lib_lbl = tk.Label(sidebar, text="BIBLIOTECA", fg=self.C("ACCENT"),
                           bg=self.C("BG_PANEL"), font=FONT_SUBTITLE)
        lib_lbl.pack(pady=(PAD_M, PAD_XS), anchor="w", padx=PAD_M)
        self._register(lib_lbl, fg="ACCENT", bg="BG_PANEL")

        star_icon = IconFactory.get("star", 16, self.C("OK"))
        self.fav_btn = tk.Button(sidebar, text=f"  Favoritos ({len(self.favorites)})",
                                 image=star_icon, compound="left",
                                 command=self.show_favorites,
                                 bg=self.C("BG_INPUT"), fg=self.C("OK"),
                                 relief="flat", anchor="w",
                                 padx=PAD_M, pady=PAD_S,
                                 activebackground=self.C("BG"),
                                 activeforeground=self.C("OK"),
                                 font=FONT_BODY, bd=0)
        self.fav_btn.image = star_icon
        self.fav_btn.pack(fill="x", padx=PAD_S, pady=PAD_XS)
        self._register(self.fav_btn, bg="BG_INPUT", fg="OK",
                       activebackground="BG", activeforeground="OK",
                       hover=("BG_INPUT", "BG_HOVER"))
        self._icon_widgets.append((self.fav_btn, "star", 16, "OK"))

        sep = tk.Frame(sidebar, bg=self.C("ACCENT_DARK"), height=1)
        sep.pack(fill="x", padx=PAD_M, pady=PAD_S)
        self._register(sep, bg="ACCENT_DARK")

        header = tk.Frame(sidebar, bg=self.C("BG_PANEL"))
        header.pack(fill="x", padx=PAD_S)
        self._register(header, bg="BG_PANEL")

        pl_lbl = tk.Label(header, text="MIS PLAYLISTS", fg=self.C("ACCENT"),
                          bg=self.C("BG_PANEL"), font=FONT_SUBTITLE)
        pl_lbl.pack(side="left", padx=PAD_XS)
        self._register(pl_lbl, fg="ACCENT", bg="BG_PANEL")

        plus_icon = IconFactory.get("plus", 14, self.C("BG"))
        pb = tk.Button(header, image=plus_icon, command=self.create_playlist,
                       bg=self.C("ACCENT"), relief="flat",
                       activebackground=self.C("ACCENT_DARK"),
                       width=24, height=24, bd=0)
        pb.image = plus_icon
        pb.pack(side="right")
        self._register(pb, bg="ACCENT", activebackground="ACCENT_DARK",
                       hover=("ACCENT", "ACCENT_HOVER"))
        self._icon_widgets.append((pb, "plus", 14, "BG"))

        self.pl_listbox = tk.Listbox(sidebar, bg=self.C("BG_PANEL"), fg=self.C("FG"),
                                     selectbackground=self.C("SELECT_BG"),
                                     selectforeground=self.C("SELECT_FG"),
                                     font=FONT_BODY, relief="flat",
                                     activestyle="none", highlightthickness=0, bd=0)
        self.pl_listbox.pack(fill="both", expand=True, padx=PAD_S, pady=PAD_S)
        self.pl_listbox.bind("<Double-Button-1>", lambda e: self.open_local_playlist())
        self.pl_listbox.bind("<ButtonRelease-3>", self._playlist_context_menu)
        self._register(self.pl_listbox, bg="BG_PANEL", fg="FG",
                       selectbackground="SELECT_BG", selectforeground="SELECT_FG")

        self._build_pl_menu()
        self._refresh_playlists_sidebar()

        right = tk.Frame(body, bg=self.C("BG"))
        right.pack(side="left", fill="both", expand=True)
        self._register(right, bg="BG")

        list_frame = tk.Frame(right, bg=self.C("BG"))
        list_frame.pack(fill="both", expand=True)
        self._register(list_frame, bg="BG")

        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")

        self.listbox = ReorderableListbox(list_frame,
                                          bg=self.C("BG_INPUT"), fg=self.C("FG"),
                                          selectbackground=self.C("SELECT_BG"),
                                          selectforeground=self.C("SELECT_FG"),
                                          font=FONT_BODY, relief="flat",
                                          yscrollcommand=scrollbar.set,
                                          activestyle="none",
                                          highlightthickness=1,
                                          highlightbackground=self.C("ACCENT_DARK"))
        self.listbox.pack(fill="both", expand=True)
        scrollbar.config(command=self.listbox.yview)
        self.listbox.bind("<Double-Button-1>", lambda e: self.play_selected())
        self.listbox.bind("<ButtonRelease-3>", self._listbox_context_menu)
        self.listbox.bind("<<ListboxReordered>>", self._on_listbox_reordered)
        self._register(self.listbox, bg="BG_INPUT", fg="FG",
                       selectbackground="SELECT_BG", selectforeground="SELECT_FG",
                       highlightbackground="ACCENT_DARK")

        self._empty_label = tk.Label(list_frame,
                                     text="Busca algo para empezar\n\n"
                                          "o abre tus favoritos / playlists",
                                     font=FONT_BODY, fg=self.C("FG_DIM"),
                                     bg=self.C("BG_INPUT"),
                                     justify="center")
        self._register(self._empty_label, fg="FG_DIM", bg="BG_INPUT")

        self._build_lb_menu()

        load_frame = tk.Frame(right, bg=self.C("BG"))
        load_frame.pack(fill="x", pady=(PAD_XS, 0))
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
                                       font=FONT_BODY_B, pady=PAD_XS,
                                       state="disabled", bd=0)
        self.load_more_btn.image = dl_icon
        self.load_more_btn.pack(fill="x")
        self._register(self.load_more_btn, bg="BG_INPUT", fg="ACCENT",
                       activebackground="ACCENT", activeforeground="BG",
                       hover=("BG_INPUT", "BG_HOVER"))
        self._icon_widgets.append((self.load_more_btn, "download", 14, "ACCENT"))

        music_icon = IconFactory.get("music", 16, self.C("OK"))
        self.now_playing = tk.Label(self.root, text="  Nada reproduciendose",
                                    image=music_icon, compound="left",
                                    fg=self.C("OK"), bg=self.C("BG"),
                                    font=FONT_BODY, wraplength=1000)
        self.now_playing.image = music_icon
        self.now_playing.pack(pady=(PAD_M, PAD_XS))
        self._register(self.now_playing, fg="OK", bg="BG")
        self._icon_widgets.append((self.now_playing, "music", 16, "OK"))

        progress_frame = tk.Frame(self.root, bg=self.C("BG"))
        progress_frame.pack(fill="x", padx=PAD_L)
        self._register(progress_frame, bg="BG")

        self.time_label = tk.Label(progress_frame, text="00:00 / 00:00",
                                   fg=self.C("FG_DIM"), bg=self.C("BG"),
                                   font=FONT_TIME, width=13, anchor="w")
        self.time_label.pack(side="left")
        self._register(self.time_label, fg="FG_DIM", bg="BG")

        self.progress_canvas = tk.Canvas(progress_frame, height=22,
                                          bg=self.C("BG"), highlightthickness=0,
                                          bd=0, cursor="hand2")
        self.progress_canvas.pack(side="left", fill="x", expand=True, padx=PAD_S)
        self._register(self.progress_canvas, bg="BG")

        self.progress_canvas.bind("<Configure>", lambda e: self._draw_progress())
        self.progress_canvas.bind("<Button-1>", self._on_progress_press)
        self.progress_canvas.bind("<B1-Motion>", self._on_progress_drag)
        self.progress_canvas.bind("<ButtonRelease-1>", self._on_progress_release)
        self.progress_canvas.bind("<Enter>", self._on_progress_enter)
        self.progress_canvas.bind("<Leave>", self._on_progress_leave)

        controls = tk.Frame(self.root, bg=self.C("BG"))
        controls.pack(pady=PAD_M)
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
                           activeforeground="BG",
                           hover=("BG_INPUT", "BG_HOVER"))
            self._icon_widgets.append((b, icon_name, size, color_key))
            return b

        icon_only_btn(controls, "prev", self.prev_song).grid(row=0, column=0, padx=PAD_XS)

        play_icon = IconFactory.get("play", 26, self.C("BG"))
        self.play_btn = tk.Button(controls, image=play_icon,
                                  command=self.toggle_play,
                                  bg=self.C("ACCENT"), relief="flat",
                                  activebackground=self.C("ACCENT_DARK"),
                                  width=50, height=40, bd=0)
        self.play_btn.image_play = play_icon
        self.play_btn.grid(row=0, column=1, padx=PAD_XS)
        self._register(self.play_btn, bg="ACCENT",
                       activebackground="ACCENT_DARK",
                       hover=("ACCENT", "ACCENT_HOVER"))

        icon_only_btn(controls, "next", self.next_song).grid(row=0, column=2, padx=PAD_XS)
        icon_only_btn(controls, "stop", self.stop_song).grid(row=0, column=3, padx=PAD_XS)

        shuffle_icon = IconFactory.get("shuffle", 22, self.C("ACCENT"))
        self._shuffle_btn = tk.Button(controls, image=shuffle_icon,
                                      command=self.toggle_shuffle,
                                      bg=self.C("BG_INPUT"), relief="flat",
                                      activebackground=self.C("ACCENT"),
                                      activeforeground=self.C("BG"),
                                      width=44, height=36, bd=0)
        self._shuffle_btn.image = shuffle_icon
        self._shuffle_btn.grid(row=0, column=4, padx=(PAD_M, PAD_XS))
        self._register(self._shuffle_btn, bg="BG_INPUT",
                       activebackground="ACCENT", activeforeground="BG",
                       hover=("BG_INPUT", "BG_HOVER"))
        self._icon_widgets.append((self._shuffle_btn, "shuffle", 22, "ACCENT"))

        repeat_icon = IconFactory.get("repeat", 22, self.C("ACCENT"))
        self._repeat_btn = tk.Button(controls, image=repeat_icon,
                                     command=self._cycle_repeat,
                                     bg=self.C("BG_INPUT"), relief="flat",
                                     activebackground=self.C("ACCENT"),
                                     activeforeground=self.C("BG"),
                                     width=44, height=36, bd=0)
        self._repeat_btn.image = repeat_icon
        self._repeat_btn.grid(row=0, column=5, padx=PAD_XS)
        self._register(self._repeat_btn, bg="BG_INPUT",
                       activebackground="ACCENT", activeforeground="BG",
                       hover=("BG_INPUT", "BG_HOVER"))
        self._icon_widgets.append((self._repeat_btn, "repeat", 22, "ACCENT"))

        vol_frame = tk.Frame(controls, bg=self.C("BG"))
        vol_frame.grid(row=0, column=6, padx=(PAD_L, PAD_XS))
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
        self.volume.pack(side="left", padx=PAD_XS)
        self.player.volume = 80
        self._register(self.volume, bg="BG", fg="ACCENT",
                       troughcolor="BG_INPUT", activebackground="ACCENT")

        bottom_bar = tk.Frame(self.root, bg=self.C("BG"))
        bottom_bar.pack(fill="x", padx=PAD_L, pady=(PAD_S, PAD_M))
        self._register(bottom_bar, bg="BG")

        self.github_link = tk.Label(bottom_bar,
                                    text=f"by IamJony  ({GITHUB_URL})",
                                    fg=self.C("FG_DIM"), bg=self.C("BG"),
                                    font=FONT_TINY, cursor="hand2")
        self.github_link.pack(side="right")
        self.github_link.bind("<Button-1>",
                              lambda e: webbrowser.open(GITHUB_URL))
        self._register(self.github_link, fg="FG_DIM", bg="BG")

        shortcuts = tk.Label(bottom_bar,
                             text="Space: Play/Pausa  ·  Ctrl+→/←: Cambiar  ·  "
                                  "Ctrl+S: Shuffle  ·  Ctrl+R: Repetir  ·  Esc: Stop",
                             font=FONT_TINY, fg=self.C("FG_DIM"), bg=self.C("BG"))
        shortcuts.pack(side="right", padx=PAD_L)
        self._register(shortcuts, fg="FG_DIM", bg="BG")

        self.status = tk.Label(bottom_bar, text="Listo", fg=self.C("FG_DIM"),
                               bg=self.C("BG"),
                               font=FONT_SMALL, anchor="w")
        self.status.pack(side="left")
        self._register(self.status, fg="FG_DIM", bg="BG")

        self._icon_pause = IconFactory.get("pause", 26, self.C("BG"))
        self._icon_play  = IconFactory.get("play", 26, self.C("BG"))

        self._update_progress()

    def _build_pl_menu(self):
        if getattr(self, "pl_menu", None) is not None:
            try:
                self.pl_menu.destroy()
            except Exception:
                pass
        self.pl_menu = tk.Menu(
            self.root, tearoff=0,
            bg=self.C("BG_PANEL"), fg=self.C("FG"),
            activebackground=self.C("ACCENT"),
            activeforeground=self.C("BG"), bd=0,
        )
        self.pl_menu.add_command(
            label="Reproducir",
            image=IconFactory.get("play", 14, self.C("ACCENT")),
            compound="left",
            command=lambda: (self._close_context_menus(), self.open_local_playlist()))
        self.pl_menu.add_command(
            label="Renombrar",
            image=IconFactory.get("edit", 14, self.C("FG")),
            compound="left",
            command=lambda: (self._close_context_menus(), self.rename_playlist()))
        self.pl_menu.add_command(
            label="Eliminar",
            image=IconFactory.get("trash", 14, self.C("DANGER")),
            compound="left",
            command=lambda: (self._close_context_menus(), self.delete_playlist()))

    def _build_lb_menu(self):
        if getattr(self, "lb_menu", None) is not None:
            try:
                self.lb_menu.destroy()
            except Exception:
                pass
        self.lb_menu = tk.Menu(
            self.root, tearoff=0,
            bg=self.C("BG_PANEL"), fg=self.C("FG"),
            activebackground=self.C("ACCENT"),
            activeforeground=self.C("BG"), bd=0,
        )
        self.lb_menu.add_command(
            label="Reproducir",
            image=IconFactory.get("play", 14, self.C("ACCENT")),
            compound="left",
            command=lambda: (self._close_context_menus(), self.play_selected()))
        self.lb_menu.add_command(
            label="Anadir/Quitar favorito",
            image=IconFactory.get("star", 14, self.C("OK")),
            compound="left",
            command=lambda: (self._close_context_menus(), self.toggle_favorite_selected()))
        self.lb_menu.add_command(
            label="Descargar MP3",
            image=IconFactory.get("download", 14, self.C("OK")),
            compound="left",
            command=lambda: (self._close_context_menus(),
                             self.download_mp3()))
        self.lb_menu.add_command(
            label="Encontrar relacionadas",
            image=IconFactory.get("search", 14, self.C("ACCENT")),
            compound="left",
            command=lambda: (self._close_context_menus(),
                             self.find_related()))
        self.lb_menu.add_separator()
        self.lb_menu.add_command(
            label="Anadir a playlist local...",
            image=IconFactory.get("plus", 14, self.C("ACCENT")),
            compound="left",
            command=lambda: (self._close_context_menus(),
                             self.add_selected_to_local_playlist()))
        self.lb_menu.add_command(
            label="Guardar playlist completa...",
            image=IconFactory.get("folder", 14, self.C("FG")),
            compound="left",
            command=lambda: (self._close_context_menus(),
                             self.save_playlist_as_local()))

    def _close_context_menus(self, event=None):
        for m in (getattr(self, "pl_menu", None), getattr(self, "lb_menu", None)):
            if m is None:
                continue
            try:
                m.unpost()
            except Exception:
                pass
        self._open_menu = None

    def _maybe_close_menus_click(self, event):
        m = getattr(self, "_open_menu", None)
        if m is None:
            return
        try:
            if event.widget is m or str(event.widget).startswith(str(m)):
                return
        except Exception:
            pass
        self._close_context_menus()

    def _popup_menu(self, menu, x, y):
        if self._closing:
            return
        self._open_menu = menu
        try:
            menu.tk_popup(x, y)
        finally:
            self.root.after_idle(menu.grab_release)

    def _open_theme_menu(self):
        if self._closing:
            return
        if self._theme_menu_open:
            self._close_theme_menu()
            return
        x = self.theme_btn.winfo_rootx()
        y = self.theme_btn.winfo_rooty() + self.theme_btn.winfo_height()
        try:
            self.theme_menu.post(x, y)
            self._theme_menu_open = True
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
        if self._closing:
            return
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
        if self._closing:
            return
        options = [t for t in THEME_ORDER if t != self.current_theme]
        if options:
            self.apply_theme(random.choice(options))

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
        if self._closing:
            return
        self.shuffle_mode = not self.shuffle_mode
        if self.shuffle_mode:
            self.shuffle_history = [self.current_index] if self.current_index >= 0 else []
            self.status.config(text="Modo aleatorio ACTIVADO")
            self.toast.show("Shuffle activado")
        else:
            self.shuffle_history = []
            self.status.config(text="Modo secuencial")
            self.toast.show("Shuffle desactivado")
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

    def _cycle_repeat(self):
        if self._closing:
            return
        self._repeat_mode = (self._repeat_mode + 1) % 3
        self._refresh_repeat_btn()
        labels = {0: "Repeat OFF", 1: "Repetir cancion", 2: "Repetir lista"}
        self.status.config(text=labels[self._repeat_mode])
        self.toast.show(labels[self._repeat_mode])

    def _refresh_repeat_btn(self):
        if not hasattr(self, "_repeat_btn"):
            return
        if self._repeat_mode == 0:
            self._repeat_btn.configure(bg=self.C("BG_INPUT"),
                                       activebackground=self.C("ACCENT"))
            color_key = "ACCENT"
        else:
            self._repeat_btn.configure(bg=self.C("ACCENT"),
                                       activebackground=self.C("ACCENT_DARK"))
            color_key = "BG"
        icon = IconFactory.get("repeat", 22, self.C(color_key))
        self._repeat_btn.configure(image=icon)
        self._repeat_btn.image = icon

    def _refresh_playlists_sidebar(self):
        if self._closing:
            return
        self.pl_listbox.delete(0, tk.END)
        for name in sorted(self.local_playlists.keys()):
            n = len(self.local_playlists[name])
            self.pl_listbox.insert(tk.END, f"  {name}   ({n})")
        self.fav_btn.config(text=f"  Favoritos ({len(self.favorites)})")

    def _selected_playlist_name(self):
        sel = self.pl_listbox.curselection()
        if not sel:
            return None
        txt = self.pl_listbox.get(sel[0])
        # Buscar coincidencia exacta (soporta nombres con/sin contador)
        for name in self.local_playlists:
            if txt.strip().startswith(name):
                return name
        # Fallback: Descargas por prefijo
        if DOWNLOADS_PLAYLIST_NAME in txt:
            return DOWNLOADS_PLAYLIST_NAME
        return None


    def _playlist_context_menu(self, event):
        if self._closing:
            return
        idx = self.pl_listbox.nearest(event.y)
        if idx >= 0:
            self.pl_listbox.selection_clear(0, tk.END)
            self.pl_listbox.selection_set(idx)
        self.root.after_idle(
            lambda: self._popup_menu(self.pl_menu, event.x_root, event.y_root))

    def is_favorite(self, url):
        return any(f["url"] == url for f in self.favorites)

    def toggle_favorite_selected(self):
        if self._closing:
            return
        sel = self.listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        if idx >= len(self.playlist):
            return
        item = self.playlist[idx]
        if item.get("type") == "playlist":
            self.toast.show("Selecciona un video, no una playlist")
            return
        if self.is_favorite(item["url"]):
            self.favorites = [f for f in self.favorites if f["url"] != item["url"]]
            self.toast.show("Quitado de favoritos")
        else:
            self.favorites.append({
                "title": item["title"], "url": item["url"],
                "duration": item.get("duration", 0)})
            self.toast.show("Anadido a favoritos")
        self._save_data()
        self._refresh_playlists_sidebar()

    def show_favorites(self):
        if self._closing:
            return
        if not self.favorites:
            self.toast.show("Aún no tienes favoritos")
            return
        self.current_query = ""
        self.current_sp = ""
        self.loaded_count = 0
        self.playlist = []
        self.listbox.delete(0, tk.END)
        self.shuffle_history = []
        self._current_playing_row = -1
        for f in self.favorites:
            duration = f.get("duration", 0)
            label = f"{f['title']}  [{fmt_time(duration)}]"
            self.playlist.append({"title": f["title"], "url": f["url"],
                                  "type": "video", "duration": duration})
            self.listbox.insert(tk.END, label)
        self.load_more_btn.config(state="disabled")
        self.status.config(text=f"{len(self.favorites)} favoritos")
        self._update_empty_state()
        self._apply_zebra()

    def create_playlist(self):
        if self._closing:
            return
        name = simpledialog.askstring("Nueva playlist", "Nombre de la playlist:",
                                      parent=self.root)
        if not name:
            return
        name = name.strip()
        if not name:
            return
        if name in self.local_playlists:
            self.toast.show("Ya existe esa playlist")
            return
        self.local_playlists[name] = []
        self._save_data()
        self._refresh_playlists_sidebar()
        self.toast.show(f"Playlist '{name}' creada")

    def open_local_playlist(self):
        if self._closing:
            return
        if (self._selected_playlist_name() == DOWNLOADS_PLAYLIST_NAME):
            self._refresh_downloads_playlist()
        name = self._selected_playlist_name()
        if not name:
            return
        items = self.local_playlists.get(name, [])
        if not items:
            self.toast.show("Playlist vacía")
            return
        self.current_query = ""
        self.current_sp = ""
        self.loaded_count = 0
        self.playlist = []
        self.listbox.delete(0, tk.END)
        self.shuffle_history = []
        self._current_playing_row = -1
        for it in items:
            duration = it.get("duration", 0)
            label = f"{it['title']}  [{fmt_time(duration)}]"
            self.playlist.append({"title": it["title"], "url": it["url"],
                                  "type": "video", "duration": duration})
            self.listbox.insert(tk.END, label)
        self.load_more_btn.config(state="disabled")
        self.status.config(text=f"Playlist '{name}' - {len(items)} canciones")
        self._update_empty_state()
        self._apply_zebra()

    def rename_playlist(self):
        if self._closing:
            return
        name = self._selected_playlist_name()
        if not name:
            return
        if name == DOWNLOADS_PLAYLIST_NAME:
            self.toast.show("No se puede renombrar Descargas")
            return
        new = simpledialog.askstring("Renombrar", "Nuevo nombre:", initialvalue=name,
                                     parent=self.root)
        if not new or new == name:
            return
        new = new.strip()
        if new in self.local_playlists:
            self.toast.show("Ya hay una playlist con ese nombre")
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
        self.toast.show("Playlist renombrada")

    def delete_playlist(self):
        if self._closing:
            return
        name = self._selected_playlist_name()
        if not name:
            return
        if name == DOWNLOADS_PLAYLIST_NAME:
            self.toast.show("No se puede eliminar Descargas")
            return
        if not messagebox.askyesno("Eliminar", f"Eliminar la playlist '{name}'?"):
            return
        del self.local_playlists[name]
        self._save_data()
        self._refresh_playlists_sidebar()
        self.toast.show(f"Playlist '{name}' eliminada")

    def add_selected_to_local_playlist(self):
        if self._closing:
            return
        sel = self.listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        if idx >= len(self.playlist):
            return
        item = self.playlist[idx]
        if item.get("type") == "playlist":
            self.toast.show("Usa 'Guardar playlist completa...'")
            return
        names = sorted(self.local_playlists.keys())
        if not names:
            if messagebox.askyesno("Sin playlists",
                                   "No tienes playlists locales. Crear una ahora?"):
                self.create_playlist()
            return

        win = tk.Toplevel(self.root)
        win.overrideredirect(True)
        win.configure(bg=self.C("BG_ELEVATED"))
        self.root.update_idletasks()
        w, h = 420, 480
        x = self.root.winfo_x() + (self.root.winfo_width() - w) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - h) // 2
        win.geometry(f"{w}x{h}+{x}+{y}")
        win.transient(self.root)
        win.grab_set()

        tk.Frame(win, bg=self.C("ACCENT"), height=3).pack(fill="x")
        hdr = tk.Frame(win, bg=self.C("BG_ELEVATED"))
        hdr.pack(fill="x", padx=PAD_M, pady=PAD_M)
        tk.Label(hdr, text="Añadir a playlist", font=FONT_SUBTITLE,
                 fg=self.C("ACCENT"), bg=self.C("BG_PANEL")).pack(side="left")
        tk.Button(hdr, text="✕", command=win.destroy, font=FONT_BODY,
                  fg=self.C("FG_DIM"), bg=self.C("BG_PANEL"),
                  relief="flat", bd=0,
                  activebackground=self.C("DANGER"),
                  activeforeground=self.C("FG")).pack(side="right")

        lb = tk.Listbox(win, bg=self.C("BG_INPUT"), fg=self.C("FG"),
                        relief="flat",
                        selectbackground=self.C("SELECT_BG"),
                        selectforeground=self.C("SELECT_FG"),
                        font=FONT_BODY, activestyle="none",
                        highlightthickness=1,
                        highlightbackground=self.C("ACCENT_DARK"))
        lb.pack(fill="both", expand=True, padx=PAD_M, pady=PAD_S)
        for n in names:
            lb.insert(tk.END, f"  {n}   ({len(self.local_playlists[n])})")

        def confirm():
            s = lb.curselection()
            if not s:
                return
            chosen = names[s[0]]
            if self.is_duplicate_in_playlist(chosen, item["url"]):
                if not messagebox.askyesno("Duplicado",
                                           "Esa canción ya está. ¿Añadir igual?"):
                    return
            self.local_playlists[chosen].append({
                "title": item["title"], "url": item["url"],
                "duration": item.get("duration", 0)})
            self._save_data()
            self._refresh_playlists_sidebar()
            self.toast.show(f"Anadido a '{chosen}'")
            win.destroy()

        tk.Button(win, text="Añadir", command=confirm,
                  bg=self.C("ACCENT"), fg=self.C("BG"), relief="flat",
                  activebackground=self.C("ACCENT_DARK"),
                  activeforeground=self.C("BG"),
                  font=FONT_BODY_B, padx=PAD_L, pady=PAD_S, bd=0).pack(pady=PAD_M)

        lb.bind("<Double-Button-1>", lambda e: confirm())

    def is_duplicate_in_playlist(self, name, url):
        return any(x["url"] == url for x in self.local_playlists.get(name, []))

    def save_playlist_as_local(self):
        if self._closing:
            return
        sel = self.listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        if idx >= len(self.playlist):
            return
        item = self.playlist[idx]
        if item.get("type") != "playlist":
            self.toast.show("Selecciona una playlist")
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
                                       f"Ya existe '{name}'. ¿Sobrescribir?"):
                return

        self.spinner.start(f"Guardando '{name}'")

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
                if self._closing:
                    return
                if not saved:
                    self.root.after(0, lambda: self.spinner.stop(
                        "La playlist está vacía"))
                    return
                self.local_playlists[name] = saved
                self._save_data()
                self.root.after(0, lambda: self._refresh_playlists_sidebar())
                self.root.after(0, lambda: self.spinner.stop(
                    f"Playlist '{name}' guardada ({len(saved)} canciones)"))
            except Exception as e:
                if self._closing:
                    return
                msg = str(e)
                self.root.after(0, lambda: self.spinner.stop(
                    f"Error: {msg}"))

        threading.Thread(target=worker, daemon=True).start()

    def _on_listbox_reordered(self):
        if self._closing:
            return
        new_labels = self.listbox.get(0, tk.END)
        old_items = list(self.playlist)
        if len(old_items) != len(new_labels):
            return
        used = [False] * len(old_items)
        new_playlist = []
        for label in new_labels:
            clean_label = label.lstrip("▶ ")
            match_idx = -1
            for i, item in enumerate(old_items):
                if used[i]:
                    continue
                dur = item.get("duration", 0)
                if item.get("type") == "playlist":
                    count = item.get("count", 0)
                    count_txt = str(count) if count else "..."
                    expected = f"[Playlist - {count_txt}] {item['title']}"
                else:
                    expected = f"{item['title']}  [{fmt_time(dur)}]"
                if expected == clean_label:
                    match_idx = i
                    break
            if match_idx >= 0:
                used[match_idx] = True
                new_playlist.append(old_items[match_idx])
            else:
                new_playlist.append(old_items[len(new_playlist)])
        self.playlist = new_playlist
        self._refresh_playing_indicator()
        self._apply_zebra()

    def _refresh_playing_indicator(self):
        if self._closing:
            return
        try:
            for i in range(self.listbox.size()):
                label = self.listbox.get(i)
                if label.startswith("▶ "):
                    self.listbox.delete(i)
                    self.listbox.insert(i, label[2:])
        except Exception:
            pass

        if 0 <= self.current_index < self.listbox.size():
            try:
                label = self.listbox.get(self.current_index)
                if not label.startswith("▶ "):
                    self.listbox.delete(self.current_index)
                    self.listbox.insert(self.current_index, f"▶ {label}")
                self.listbox.itemconfig(self.current_index,
                                        fg=self.C("BG"),
                                        bg=self.C("ACCENT"))
            except Exception:
                pass

        self._apply_zebra()

    def _refresh_all_listbox_colors(self):
        if self._closing:
            return
        try:
            for i in range(self.listbox.size()):
                if i == self.current_index:
                    self.listbox.itemconfig(i,
                                            bg=self.C("ACCENT"),
                                            fg=self.C("BG"))
                else:
                    bg = self.C("BG_INPUT") if i % 2 == 0 else self.C("BG_ALT")
                    self.listbox.itemconfig(i, bg=bg, fg=self.C("FG"))
        except Exception:
            pass

        try:
            for i in range(self.pl_listbox.size()):
                self.pl_listbox.itemconfig(i,
                                           bg=self.C("BG_PANEL"),
                                           fg=self.C("FG"))
        except Exception:
            pass

    def _apply_zebra(self):
        if self._closing:
            return
        try:
            for i in range(self.listbox.size()):
                if i == self.current_index:
                    continue
                bg = self.C("BG_INPUT") if i % 2 == 0 else self.C("BG_ALT")
                self.listbox.itemconfig(i, bg=bg, fg=self.C("FG"))
        except Exception:
            pass

    def _update_empty_state(self):
        try:
            if self.listbox.size() == 0:
                self._empty_label.place(relx=0.5, rely=0.5, anchor="center")
            else:
                self._empty_label.place_forget()
        except Exception:
            pass

    def _listbox_context_menu(self, event):
        if self._closing:
            return
        idx = self.listbox.nearest(event.y)
        if idx >= 0:
            self.listbox.selection_clear(0, tk.END)
            self.listbox.selection_set(idx)
        if 0 <= idx < len(self.playlist):
            is_pl = self.playlist[idx].get("type") == "playlist"
            try:
                if is_pl:
                    self.lb_menu.entryconfig("Guardar playlist completa...", state="normal")
                    self.lb_menu.entryconfig("Anadir/Quitar favorito", state="disabled")
                    self.lb_menu.entryconfig("Anadir a playlist local...", state="disabled")
                    self.lb_menu.entryconfig("Descargar MP3", state="disabled")
                    self.lb_menu.entryconfig("Encontrar relacionadas", state="disabled")
                else:
                    self.lb_menu.entryconfig("Guardar playlist completa...", state="disabled")
                    self.lb_menu.entryconfig("Anadir/Quitar favorito", state="normal")
                    self.lb_menu.entryconfig("Anadir a playlist local...", state="normal")
                    self.lb_menu.entryconfig("Descargar MP3", state="normal")
                    self.lb_menu.entryconfig("Encontrar relacionadas", state="normal")
            except Exception:
                pass
        self.root.after_idle(
            lambda: self._popup_menu(self.lb_menu, event.x_root, event.y_root))

    def _get_filter_sp(self):
        t = self.search_type.get()
        if t in ("Canciones", "Videos"):
            return YT_FILTER_SONGS
        elif t == "Playlists":
            return YT_FILTER_PLAYLISTS
        return YT_FILTER_ALL

    def search(self):
        if self._closing:
            return
        query = self.search_entry.get().strip()
        if not query:
            self.toast.show("Escribe algo para buscar")
            return
        self.current_query = query
        self.current_sp = self._get_filter_sp()
        self.loaded_count = 0
        self.playlist.clear()
        self.listbox.delete(0, tk.END)
        self.shuffle_history = []
        self._current_playing_row = -1
        self.load_more_btn.config(state="disabled")
        self._update_empty_state()
        self.spinner.start("Buscando")
        self._fetch_page()

    def load_more(self):
        if self._closing:
            return
        if self.loading or not self.current_query:
            return
        self.load_more_btn.config(state="disabled")
        self.spinner.start("Cargando más")
        self._fetch_page()

    def _extract_artist(self, title):
        """Intenta extraer el nombre del artista del titulo."""
        if not title:
            return ""
        # Quitar sufijos comunes entre parentesis: (Official Video), [HD], etc.
        clean = re.sub(
            r"\s*[\(\[][^\)\]]*[\)\]]\s*$", "", title, flags=re.IGNORECASE
        )
        clean = re.sub(
            r"\s*\((?:official|video|audio|lyric|hd|hq|mv|m/v|live)[^\)]*\)",
            "", clean, flags=re.IGNORECASE
        )
        # Separadores comunes: " - ", " – ", " — ", " | ", " · "
        for sep in [" - ", " – ", " — ", " | ", " · "]:
            if sep in clean:
                left, right = clean.split(sep, 1)
                # Heuristica: el artista suele estar a la izquierda
                return left.strip()
        # Si no hay separador, tomar las primeras 2-3 palabras
        words = clean.strip().split()
        return " ".join(words[:3]) if words else clean.strip()

    def find_related(self):
        """Busca canciones del mismo artista y las carga en la listbox."""
        if self._closing:
            return
        sel = self.listbox.curselection()
        if not sel:
            self.toast.show("Selecciona una cancion primero")
            return
        idx = sel[0]
        if idx >= len(self.playlist):
            return
        item = self.playlist[idx]
        if item.get("type") not in ("video", "local"):
            self.toast.show("Selecciona una cancion, no una playlist")
            return

        title = item.get("title", "")
        artist = self._extract_artist(title)
        if not artist:
            self.toast.show("No se pudo detectar el artista")
            return

        # Construir query
        query = f"{artist} mix similar songs"

        # Reutilizar el flujo de busqueda existente
        self.current_query = query
        self.current_sp = YT_FILTER_SONGS
        self.loaded_count = 0
        self.playlist.clear()
        self.listbox.delete(0, tk.END)
        self.shuffle_history = []
        self._current_playing_row = -1
        self.load_more_btn.config(state="disabled")
        self._update_empty_state()
        self.spinner.start(f"Buscando similares a {artist[:25]}")
        self._fetch_page()

    def _fetch_page(self):
        if self._closing or self.loading:
            return
        self.loading = True
        threading.Thread(
            target=self._search_thread,
            args=(self.current_query, self.current_sp, self.loaded_count),
            daemon=True,
        ).start()

    def _search_thread(self, query, sp, start_index):
        try:
            with self._search_lock:
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
            if self._closing:
                return
            self.root.after(0, lambda: self._apply_search_results(entries))
        except Exception as e:
            if self._closing:
                return
            msg = str(e)
            self.root.after(0, lambda: self._on_page_error(msg))

    def _apply_search_results(self, entries):
        if self._closing:
            return
        if not entries:
            self._on_page_loaded(0, False)
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
            if not url:
                continue
            duration = entry.get("duration") or 0
            if is_playlist:
                count = entry.get("playlist_count") or entry.get("n_entries") or 0
                count_txt = str(count) if count else "..."
                label = f"[Playlist - {count_txt}] {title}"
                item = {"title": title, "url": url, "type": "playlist",
                        "count": count}
                idx = len(self.playlist)
                self.playlist.append(item)
                self.listbox.insert(tk.END, label)
                if not count:
                    playlist_jobs.append((idx, url))
            else:
                label = f"{title}  [{fmt_time(duration)}]"
                item = {"title": title, "url": url, "type": "video",
                        "duration": int(duration)}
                self.playlist.append(item)
                self.listbox.insert(tk.END, label)
            new_items += 1
        self.loaded_count = len(self.playlist)
        for idx, url in playlist_jobs:
            threading.Thread(target=self._count_playlist,
                             args=(idx, url), daemon=True).start()
        has_more = new_items >= PAGE_SIZE
        self._on_page_loaded(new_items, has_more)
        self._apply_zebra()
        self._update_empty_state()

    def _on_page_loaded(self, new_items, has_more):
        if self._closing:
            return
        self.loading = False
        total = len(self.playlist)
        if new_items == 0:
            self.spinner.stop(f"No hay más resultados ({total})")
            self.load_more_btn.config(state="disabled")
        else:
            self.spinner.stop(f"{new_items} nuevos · total {total}")
            self.load_more_btn.config(state="normal" if has_more else "disabled")

    def _on_page_error(self, msg):
        if self._closing:
            return
        self.loading = False
        self.spinner.stop(f"Error: {msg}")
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
            if self._closing:
                return
            if count and 0 <= index < len(self.playlist):
                self.playlist[index]["count"] = count
                title = self.playlist[index]["title"]
                new_label = f"[Playlist - {count}] {title}"
                self.root.after(0, lambda: self._update_listbox_item(index, new_label))
        except Exception:
            pass

    def _update_listbox_item(self, index, text):
        if self._closing:
            return
        if not (0 <= index < self.listbox.size()):
            return
        selected = list(self.listbox.curselection())
        self.listbox.delete(index)
        self.listbox.insert(index, text)
        for i in selected:
            self.listbox.selection_set(i)
        self._apply_zebra()
        self._refresh_playing_indicator()

    def play_selected(self):
        if self._closing:
            return
        sel = self.listbox.curselection()
        if not sel:
            return
        self.current_index = sel[0]
        self._play_index()

    def _play_index(self):
        if self._closing:
            return
        if not (0 <= self.current_index < len(self.playlist)):
            return
        song = self.playlist[self.current_index]
        if not song.get("url"):
            self.toast.show("URL inválida")
            return
        if song.get("type") == "playlist":
            self.status.config(text=f"Cargando playlist: {song['title'][:40]}...")
            self.now_playing.config(text=f"  Playlist: {song['title'][:70]}")
            threading.Thread(target=self._expand_playlist,
                             args=(song,), daemon=True).start()
            return
        self.now_playing.config(text=f"  {song['title'][:80]}")
        self.spinner.start("Obteniendo stream")
        self._refresh_playing_indicator()
        self._apply_zebra()
        self._notified_current = False
        threading.Thread(target=self._stream_thread, args=(song,), daemon=True).start()

    def _expand_playlist(self, playlist_item):
        try:
            ydl_opts = {"quiet": True, "no_warnings": True,
                        "extract_flat": True, "skip_download": True}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(playlist_item["url"], download=False)
                entries = info.get("entries", [])
            if self._closing:
                return
            added = 0
            for entry in entries:
                if not entry:
                    continue
                title = entry.get("title", "Desconocido")
                url = entry.get("url") or f"https://www.youtube.com/watch?v={entry.get('id')}"
                duration = entry.get("duration") or 0
                new_item = {"title": title, "url": url, "type": "video",
                            "duration": int(duration)}
                self.playlist.append(new_item)
                label = f"{title}  [{fmt_time(duration)}]"
                self.root.after(0, lambda l=label: self.listbox.insert(tk.END, l))
                added += 1
            if added > 0:
                first_new = len(self.playlist) - added
                self.current_index = first_new
                self.root.after(0, lambda: self._apply_zebra())
                self.root.after(0, lambda i=first_new: self.listbox.see(i))
                self.root.after(0, lambda: self._update_empty_state())
                self._play_index()
            else:
                self.root.after(0, lambda: self.toast.show("Playlist vacía"))
        except Exception as e:
            if self._closing:
                return
            msg = str(e)
            self.root.after(0, lambda: self.spinner.stop(f"Error: {msg}"))

    def _stream_thread(self, song):
        try:
            url = song["url"]

            # Archivo local (playlist Descargas)
            if url.startswith("file://"):
                local_path = url[len("file://"):]
                if not os.path.isfile(local_path):
                    raise Exception("Archivo no encontrado: " + local_path)
                self._ended = False
                self._last_duration = 0.0
                self._seek_guard_until = 0.0
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
                self.player.play(local_path)
                self.player.pause = False
                self.is_paused = False
                pause_icon = IconFactory.get("pause", 26, self.C("BG"))
                self._icon_pause = pause_icon
                self.root.after(0, lambda: self.play_btn.config(image=pause_icon))
                return

            now = time.time()
            cached = self._stream_cache.get(url)
            if cached and (now - cached[0]) < STREAM_CACHE_TTL:
                stream_url = cached[1]
            else:
                ydl_opts = {"format": "bestaudio/best", "quiet": True,
                            "no_warnings": True}
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    stream_url = info.get("url")
                    if not stream_url:
                        formats = info.get("formats", [])
                        audio_formats = [f for f in formats if f.get("vcodec") == "none"]
                        if audio_formats:
                            stream_url = audio_formats[-1]["url"]
                if stream_url:
                    self._stream_cache[url] = (now, stream_url)
                    while len(self._stream_cache) > STREAM_CACHE_MAX:
                        self._stream_cache.popitem(last=False)
            if self._closing:
                return
            if not stream_url:
                raise Exception("No se pudo obtener URL")

            self._ended = False
            self._last_duration = 0.0
            self._seek_guard_until = 0.0
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
        except Exception as e:
            if self._closing:
                return
            msg = str(e)
            self.root.after(0, lambda: self.spinner.stop(f"Error: {msg}"))

    def _on_track_end(self):
        if self._closing:
            return
        if time.time() < self._seek_guard_until:
            return
        with self._end_lock:
            if self._ended or self._starting:
                return
            self._ended = True
        self.root.after(300, self._advance_after_end)

    def _advance_after_end(self):
        if self._closing:
            return
        if self.current_index < 0:
            return
        try:
            busy = self.player.core_idle is False
        except Exception:
            busy = False
        if busy:
            self._ended = False
            return

        if self._repeat_mode == 1:
            self._play_index()
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
        elif self._repeat_mode == 2 and len(self.playlist) > 0:
            self.current_index = 0
            self._play_index()
        else:
            self.status.config(text="Fin de la lista")
            self._refresh_playing_indicator()

    def _scan_downloads(self):
        """Escanea la carpeta de descargas y devuelve lista de items."""
        if self._closing:
            return []
        ddir = self._ensure_download_dir()
        if not ddir:
            return []
        items = []
        try:
            import glob as _glob
            for mp3_path in sorted(
                _glob.glob(os.path.join(ddir, "*.mp3")),
                key=lambda p: os.path.getmtime(p),
                reverse=True,
            ):
                if not os.path.isfile(mp3_path):
                    continue
                name = os.path.splitext(os.path.basename(mp3_path))[0]
                items.append({
                    "title": name,
                    "url": "file://" + mp3_path,
                    "type": "local",
                    "duration": 0,
                    "path": mp3_path,
                })
        except Exception as e:
            print(f"[scan_downloads] Error: {e}")
        return items

    def _refresh_downloads_playlist(self):
        """Actualiza la playlist Descargas (lista dinamica)."""
        if self._closing:
            return
        items = self._scan_downloads()
        self.local_playlists[DOWNLOADS_PLAYLIST_NAME] = items

    def _ensure_download_dir(self):
        candidates = [DOWNLOAD_DIR]
        try:
            home = os.path.expanduser("~")
            if home and home != "~":
                candidates.append(os.path.join(home, "ytmusic-dlp"))
                candidates.append(os.path.join(home, "Music", "ytmusic-dlp"))
        except Exception:
            pass
        try:
            import tempfile
            candidates.append(os.path.join(tempfile.gettempdir(), "ytmusic-dlp"))
        except Exception:
            pass

        seen = set()
        for cand in candidates:
            if not cand:
                continue
            try:
                norm = os.path.abspath(os.path.expanduser(cand))
            except Exception:
                continue
            if norm in seen:
                continue
            seen.add(norm)
            try:
                os.makedirs(norm, exist_ok=True)
                if os.access(norm, os.W_OK):
                    return norm
            except (OSError, PermissionError) as e:
                print(f"[download] No se pudo crear {cand}: {e}")
            except Exception as e:
                print(f"[download] Error con {cand}: {e}")
        return None

    def download_mp3(self):
        if self._closing:
            return
        sel = self.listbox.curselection()
        if not sel:
            self.toast.show("Selecciona una canción")
            return
        idx = sel[0]
        if idx >= len(self.playlist):
            return
        item = self.playlist[idx]
        if item.get("type") == "playlist":
            self.toast.show("Selecciona un video, no playlist")
            return
        if not item.get("url"):
            self.toast.show("URL inválida")
            return

        download_dir = self._ensure_download_dir()
        if not download_dir:
            self.toast.show("No se pudo crear la carpeta de descargas")
            return

        self.spinner.start(f"Descargando: {item['title'][:30]}")

        def worker():
            try:
                try:
                    os.makedirs(download_dir, exist_ok=True)
                except Exception:
                    pass

                outtmpl = os.path.join(download_dir, "%(title)s.%(ext)s")
                ydl_opts = {
                    "format": "bestaudio/best",
                    "outtmpl": outtmpl,
                    "quiet": True,
                    "no_warnings": True,
                    "noplaylist": True,
                    "retries": 3,
                    "fragment_retries": 3,
                    "postprocessors": [{
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": "192",
                    }],
                    "ffmpeg_location": os.environ.get("FFMPEG_BINARY", "ffmpeg"),
                }
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([item["url"]])

                if self._closing:
                    return

                title = item["title"]
                title_short = title[:60]

                final_path = download_dir
                try:
                    import glob as _glob
                    candidates = sorted(
                        _glob.glob(os.path.join(download_dir, "*.mp3")),
                        key=os.path.getmtime, reverse=True
                    )
                    if candidates:
                        final_path = candidates[0]
                except Exception:
                    pass

                def _on_success():
                    try:
                        self.spinner.stop(f"Descargado: {title_short}")
                    except Exception:
                        pass

                self.root.after(0, _on_success)

                self.root.after(0, self._refresh_downloads_playlist)
                self.root.after(0, self._refresh_playlists_sidebar)

                try:
                    size_str = ""
                    try:
                        size_mb = os.path.getsize(final_path) / (1024 * 1024)
                        size_str = f" ({size_mb:.1f} MB)"
                    except Exception:
                        pass
                    msg = f"{title}{size_str}\nGuardado en: {final_path}"
                    self._notify("Descarga completa", msg)
                except Exception:
                    pass
            except Exception as e:
                if self._closing:
                    return
                msg = str(e)
                import sys as _sys
                print(f"[download_mp3] ERROR: {msg}", file=_sys.stderr)
                self.root.after(0, lambda: self.spinner.stop(
                    f"Error: {msg[:60]}"))

        threading.Thread(target=worker, daemon=True).start()

    def toggle_play(self):
        if self._closing:
            return
        if self.current_index < 0:
            self.play_selected()
            return
        if self.player.pause:
            self.player.pause = False
            self.is_paused = False
            icon = IconFactory.get("pause", 26, self.C("BG"))
            self._icon_pause = icon
            self.play_btn.config(image=icon)
            self.status.config(text="Reproduciendo")
        else:
            self.player.pause = True
            self.is_paused = True
            icon = IconFactory.get("play", 26, self.C("BG"))
            self._icon_play = icon
            self.play_btn.config(image=icon)
            self.status.config(text="Pausado")

    def stop_song(self):
        if self._closing:
            return
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
        self._refresh_playing_indicator()
        self._apply_zebra()
        self.status.config(text="Detenido")

    def next_song(self):
        if self._closing:
            return
        self._advance(direction=+1)

    def prev_song(self):
        if self._closing:
            return
        self._advance(direction=-1)

    def _advance(self, direction):
        if direction > 0 and self.shuffle_mode:
            idx = self._next_shuffle_index()
            if idx is not None:
                self.shuffle_history.append(idx)
                self.current_index = idx
                self.listbox.selection_clear(0, tk.END)
                self.listbox.selection_set(idx)
                self.listbox.see(idx)
                self._play_index()
                return
        new_idx = self.current_index + direction
        if 0 <= new_idx < len(self.playlist):
            self.current_index = new_idx
            self.listbox.selection_clear(0, tk.END)
            self.listbox.selection_set(new_idx)
            self.listbox.see(new_idx)
            self._play_index()

    def _on_volume(self, value):
        if self._closing:
            return
        try:
            self.player.volume = float(value)
        except Exception:
            pass

    def _on_progress_enter(self, event):
        self._hover_progress = True
        self._draw_progress()

    def _on_progress_leave(self, event):
        self._hover_progress = False
        self._draw_progress()

    def _on_progress_press(self, event):
        if self._closing or self._last_duration <= 0:
            return
        self._seeking = True
        self._update_seek_from_x(event.x)

    def _on_progress_drag(self, event):
        if self._closing:
            return
        if self._seeking:
            self._update_seek_from_x(event.x)

    def _on_progress_release(self, event):
        if self._closing or not self._seeking:
            return
        self._update_seek_from_x(event.x)
        self._seeking = False
        try:
            if self._seek_value > 0:
                self.player.time_pos = self._seek_value
                self._seek_guard_until = time.time() + 1.8
                self._idle_strikes = 0
                self._ended = False
                self._buffering = False
        except Exception:
            pass

    def _update_seek_from_x(self, x):
        if self._closing:
            return
        try:
            w = self.progress_canvas.winfo_width()
            if w <= 0 or self._last_duration <= 0:
                return
            ratio = max(0.0, min(1.0, x / w))
            self._seek_value = ratio * self._last_duration
            self._draw_progress(preview_ratio=ratio)
            self.time_label.config(
                text=f"{fmt_time(self._seek_value)} / {fmt_time(self._last_duration)}")
        except Exception:
            pass

    def _draw_progress(self, preview_ratio=None):
        if self._closing:
            return
        try:
            c = self.progress_canvas
            w = c.winfo_width()
            h = c.winfo_height()
            if w <= 1 or h <= 1:
                return

            c.delete("all")
            bar_h = 8
            y0 = (h - bar_h) // 2
            y1 = y0 + bar_h
            radius = bar_h // 2

            def rounded_bar(x0, x1, color):
                if x1 - x0 < 1:
                    return
                c.create_rectangle(x0 + radius, y0, x1 - radius, y1,
                                   fill=color, outline=color)
                c.create_oval(x0, y0, x0 + 2*radius, y1,
                              fill=color, outline=color)
                c.create_oval(x1 - 2*radius, y0, x1, y1,
                              fill=color, outline=color)

            rounded_bar(0, w, self.C("BG_INPUT"))

            dur = self._last_duration
            if dur > 0:
                try:
                    cache = self.player.demuxer_cache_time or 0
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
            cy = h // 2
            r = 9 if (self._hover_progress or self._seeking) else 6

            if self._hover_progress or self._seeking:
                c.create_oval(mx-r-3, cy-r-3, mx+r+3, cy+r+3,
                              fill=self.C("ACCENT_GLOW"), outline="")
            c.create_oval(mx-r, cy-r, mx+r, cy+r,
                          fill=self.C("ACCENT"), outline=self.C("FG"), width=2)
        except Exception:
            pass

    def _update_progress(self):
        if self._closing:
            return
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
                    started = (pos_chk is not None and pos_chk > 0.3) \
                              or (not idle_chk) or (elapsed > 8.0)
                    if started:
                        self._starting = False
                        self._idle_strikes = 0
                        self.spinner.stop("Reproduciendo")
                        if not self._notified_current:
                            self._notified_current = True
                            if 0 <= self.current_index < len(self.playlist):
                                song = self.playlist[self.current_index]
                                if song.get("type") != "playlist":
                                    self._notify("Reproduciendo",
                                                 song["title"][:120])

                if self._starting:
                    if not self._closing:
                        self._progress_job = self.root.after(500, self._update_progress)
                    return

                try:
                    buffering = bool(self.player.paused_for_cache) or bool(self.player.core_idle)
                except Exception:
                    buffering = False
                if buffering and not self.is_paused:
                    if not self._buffering:
                        self._buffering = True
                        self.spinner.start("Buffering")
                else:
                    if self._buffering:
                        self._buffering = False
                        self.spinner.stop("Reproduciendo")

                if not self._seeking:
                    try:
                        pos = self.player.time_pos or 0
                    except Exception:
                        pos = 0
                    if dur > 0:
                        self.time_label.config(
                            text=f"{fmt_time(pos)} / {fmt_time(dur)}")
                    self._draw_progress()

                in_seek_guard = time.time() < self._seek_guard_until
                if (not self.is_paused and not self._ended
                        and not self._buffering and not self._starting
                        and not self._seeking and not in_seek_guard):
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
                else:
                    self._idle_strikes = 0
        except Exception:
            pass
        if not self._closing:
            self._progress_job = self.root.after(500, self._update_progress)

    def export_data(self):
        if self._closing:
            return
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
            self.toast.show(f"Exportado a {os.path.basename(path)}")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo exportar: {e}")

    def import_data(self):
        if self._closing:
            return
        path = filedialog.askopenfilename(
            title="Importar biblioteca",
            filetypes=[("JSON", "*.json"), ("Todos los archivos", "*.*")])
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo leer: {e}")
            return
        favs = data.get("favorites", [])
        pls = data.get("local_playlists", {})
        if not favs and not pls:
            self.toast.show("Archivo vacío")
            return
        choice = messagebox.askyesnocancel(
            "Importar",
            "Si = Fusionar\nNo = Reemplazar\nCancelar = Cancelar")
        if choice is None:
            return
        if choice:
            existing_urls = {f["url"] for f in self.favorites}
            for f in favs:
                if f.get("url") and f["url"] not in existing_urls:
                    self.favorites.append(f)
                    existing_urls.add(f["url"])
            for name, items in pls.items():
                if name in self.local_playlists:
                    existing = {x["url"] for x in self.local_playlists[name]}
                    for it in items:
                        if it.get("url") and it["url"] not in existing:
                            self.local_playlists[name].append(it)
                            existing.add(it["url"])
                else:
                    self.local_playlists[name] = items
            self.toast.show("Fusionado")
        else:
            self.favorites = favs
            self.local_playlists = pls
            self.toast.show("Reemplazado")
        self._save_data()
        self._refresh_playlists_sidebar()

    def _notify(self, title, message):
        notify(title, message)

    def on_close(self):
        if getattr(self, "_closing", False):
            return
        self._closing = True

        if self._progress_job is not None:
            try:
                self.root.after_cancel(self._progress_job)
            except Exception:
                pass
            self._progress_job = None

        try:
            self._save_data()
            self._save_theme_setting()
        except Exception:
            pass

        for m in (getattr(self, "pl_menu", None),
                  getattr(self, "lb_menu", None),
                  getattr(self, "theme_menu", None)):
            if m is None:
                continue
            try:
                m.unpost()
                m.grab_release()
            except Exception:
                pass

        try:
            self.root.destroy()
        except Exception:
            pass

        def _shutdown():
            try:
                self.player.stop()
                self.player.terminate()
            except Exception:
                pass

        threading.Thread(target=_shutdown, daemon=True).start()
