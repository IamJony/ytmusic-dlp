import tkinter as tk

from src.utils.bin_paths import setup_env
from src.core.player_app import YouTubeMusicPlayer


def main():
    setup_env()
    root = tk.Tk()
    app = YouTubeMusicPlayer(root)
    root.mainloop()


if __name__ == "__main__":
    main()
