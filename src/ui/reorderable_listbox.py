import tkinter as tk


class ReorderableListbox(tk.Listbox):
    """Listbox con drag & drop para reordenar filas."""
    def __init__(self, master, **kw):
        kw['selectmode'] = tk.BROWSE
        tk.Listbox.__init__(self, master, **kw)
        self._drag_start = None
        self.bind('<Button-1>', self._on_press, add="+")
        self.bind('<B1-Motion>', self._on_drag, add="+")
        self.bind('<ButtonRelease-1>', self._on_release, add="+")

    def _on_press(self, event):
        self._drag_start = self.nearest(event.y)

    def _on_drag(self, event):
        if self._drag_start is None:
            return
        target = self.nearest(event.y)
        if target == self._drag_start:
            return
        text = self.get(self._drag_start)
        self.delete(self._drag_start)
        self.insert(target, text)
        self.selection_clear(0, tk.END)
        self.selection_set(target)
        self._drag_start = target
        self.event_generate("<<ListboxReordered>>")

    def _on_release(self, event):
        self._drag_start = None
