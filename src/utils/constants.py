import os

YT_FILTER_ALL       = ""
YT_FILTER_SONGS     = "EgIQAQ%3D%3D"
YT_FILTER_VIDEOS    = "EgIQAQ%3D%3D"
YT_FILTER_PLAYLISTS = "EgIQAw%3D%3D"

PAGE_SIZE = 30
DATA_FILE = os.path.join(os.path.expanduser("~"), ".yt_music_player_data.json")
SETTINGS_FILE = os.path.join(os.path.expanduser("~"), ".yt_music_player_settings.json")
DOWNLOAD_DIR = os.path.join(os.path.expanduser("~"), "Downloads", "ytmusic-dlp")

GITHUB_URL = "https://github.com/IamJony"
APP_VERSION = "1.1.0"

STREAM_CACHE_TTL = 3 * 3600  # 3 horas (más conservador)
STREAM_CACHE_MAX = 200       # límite de entradas
