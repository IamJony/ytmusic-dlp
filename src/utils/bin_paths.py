"""Resuelve rutas a binarios incluidos en el bundle o del sistema."""
import os
import sys
import shutil


def _meipass():
    return getattr(sys, "_MEIPASS", None)


def get_ffmpeg_path():
    base = _meipass()
    if base:
        for p in (os.path.join(base, "ffmpeg"),
                  os.path.join(base, "bin", "ffmpeg")):
            if os.path.isfile(p):
                return p
    return shutil.which("ffmpeg") or "ffmpeg"


def get_mpv_binary():
    base = _meipass()
    if base:
        for p in (os.path.join(base, "mpv"),
                  os.path.join(base, "bin", "mpv")):
            if os.path.isfile(p):
                return p
    return shutil.which("mpv") or "mpv"


def setup_env():
    """Prepara PATH/LD_LIBRARY_PATH y FFMPEG_BINARY al arrancar."""
    base = _meipass()
    if not base:
        return
    for env_name in ("PATH", "LD_LIBRARY_PATH"):
        current = os.environ.get(env_name, "")
        parts = current.split(os.pathsep) if current else []
        if base not in parts:
            parts.insert(0, base)
        os.environ[env_name] = os.pathsep.join(parts)
    ffmpeg = get_ffmpeg_path()
    if os.path.isfile(ffmpeg):
        os.environ["FFMPEG_BINARY"] = ffmpeg
