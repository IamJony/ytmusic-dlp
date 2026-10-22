"""Componentes de feedback visual: toast in-app y spinner."""
import tkinter as tk

try:
    from src.ui.styles import (FONT_BODY, FONT_TIME, PAD_L, PAD_S,
                                SPINNER_FRAMES)
except ImportError:
    FONT_BODY = ("Segoe UI", 10)
    FONT_TIME = ("Consolas", 9)
    PAD_L, PAD_S = 16, 8
    SPINNER_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]


class Toast:
    """Notificación tipo toast en la esquina inferior derecha."""

    def __init__(self, root, colors_getter):
        self.root = root
        self.C = colors_getter
        self._current = None

    def show(self, message, duration=3000):
        try:
            if self._current is not None and self._current.winfo_exists():
                self._current.destroy()
        except Exception:
            pass

        try:
            bg = self.C("ACCENT")
            fg = self.C("BG")
        except Exception:
            bg, fg = "#00e5ff", "#0a0e14"

        t = tk.Toplevel(self.root)
        t.overrideredirect(True)
        t.configure(bg=bg)
        try:
            t.attributes("-alpha", 0.96)
            t.attributes("-topmost", True)
        except Exception:
            pass

        label = tk.Label(t, text=message, bg=bg, fg=fg,
                         font=FONT_BODY, padx=PAD_L, pady=PAD_S)
        label.pack()

        try:
            self.root.update_idletasks()
            w = label.winfo_reqwidth() + 20
            h = label.winfo_reqheight() + 16
            x = self.root.winfo_x() + self.root.winfo_width() - w - 24
            y = self.root.winfo_y() + self.root.winfo_height() - h - 80
            t.geometry(f"{w}x{h}+{x}+{y}")
        except Exception:
            pass

        self._current = t
        t.after(duration, lambda: self._safe_destroy(t))

    def _safe_destroy(self, t):
        try:
            if t.winfo_exists():
                t.destroy()
        except Exception:
            pass
        if self._current is t:
            self._current = None


class Spinner:
    """Animación de spinner braille en un Label de status."""

    def __init__(self, root, label_widget):
        self.root = root
        self.label = label_widget
        self._frame = 0
        self._running = False
        self._job = None
        self._prefix = "Cargando"

    def start(self, prefix="Cargando"):
        # Evitar reiniciar si ya está corriendo con el mismo texto
        # (doble start produce dos animaciones compitiendo → "letras locas")
        if self._running and self._prefix == prefix:
            return
        self.stop()
        self._running = True
        self._prefix = prefix
        self._frame = 0

        def tick():
            if not self._running:
                return
            try:
                frame = SPINNER_FRAMES[self._frame % len(SPINNER_FRAMES)]
                self.label.config(text=f"{frame}  {self._prefix}...")
            except Exception:
                return
            self._frame += 1
            self._job = self.root.after(80, tick)

        tick()

    def stop(self, final_text=None):
        self._running = False
        if self._job is not None:
            try:
                self.root.after_cancel(self._job)
            except Exception:
                pass
            self._job = None
        if final_text is not None:
            try:
                self.label.config(text=final_text)
            except Exception:
                pass
