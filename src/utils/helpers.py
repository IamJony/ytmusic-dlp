import subprocess
import sys


def ps_escape(text: str) -> str:
    return text.replace("'", "''")


def notify(title: str, message: str) -> None:
    """Notificación multiplataforma con fallback en cascada."""
    import threading

    try:
        from plyer import notification as plyer_notification
    except Exception:
        plyer_notification = None

    def _do():
        # Windows
        if sys.platform.startswith("win"):
            if plyer_notification is not None:
                try:
                    plyer_notification.notify(title=title, message=message,
                                              app_name="ytmusic-dlp", timeout=4)
                    return
                except Exception:
                    pass
            try:
                ps = (
                    "[Windows.UI.Notifications.ToastNotificationManager, "
                    "Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null; "
                    "$template = [Windows.UI.Notifications.ToastNotificationManager]::"
                    "GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::"
                    "ToastText02); "
                    "$textNodes = $template.GetElementsByTagName('text'); "
                    "$textNodes.Item(0).AppendChild($template.CreateTextNode("
                    f"'{ps_escape(title)}')) | Out-Null; "
                    "$textNodes.Item(1).AppendChild($template.CreateTextNode("
                    f"'{ps_escape(message)}')) | Out-Null; "
                    "$toast = [Windows.UI.Notifications.ToastNotification]::new($template); "
                    "[Windows.UI.Notifications.ToastNotificationManager]::"
                    "CreateToastNotifier('ytmusic-dlp').Show($toast);"
                )
                subprocess.run(["powershell", "-NoProfile", "-WindowStyle", "Hidden",
                                "-Command", ps], check=False, timeout=4,
                               creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            except Exception:
                pass
            return

        # macOS
        if sys.platform == "darwin":
            try:
                safe_title = title.replace('"', '\\"')
                safe_msg = message.replace('"', '\\"')
                subprocess.run(["osascript", "-e",
                                f'display notification "{safe_msg}" with title "{safe_title}"'],
                               check=False, timeout=3)
                return
            except Exception:
                pass
            if plyer_notification is not None:
                try:
                    plyer_notification.notify(title=title, message=message,
                                              app_name="ytmusic-dlp", timeout=4)
                except Exception:
                    pass
            return

        # Linux
        try:
            subprocess.run(["notify-send", "-a", "ytmusic-dlp", "-t", "4000",
                            title, message], check=False, timeout=3,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return
        except FileNotFoundError:
            pass
        except Exception:
            pass
        if plyer_notification is not None:
            try:
                plyer_notification.notify(title=title, message=message,
                                          app_name="ytmusic-dlp", timeout=4)
                return
            except Exception:
                pass
        try:
            subprocess.run(["kdialog", "--title", title, "--passivepopup", message, "4"],
                           check=False, timeout=3,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

    threading.Thread(target=_do, daemon=True).start()


def fmt_time(seconds: int) -> str:
    seconds = int(seconds)
    m, s = divmod(seconds, 60)
    return f"{m:02d}:{s:02d}"


def hex_to_rgb(hex_color: str):
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def blend(c1: str, c2: str, ratio: float) -> str:
    """Mezcla dos colores hex. ratio=0 → c1, ratio=1 → c2."""
    r1, g1, b1 = hex_to_rgb(c1)
    r2, g2, b2 = hex_to_rgb(c2)
    r = int(r1 + (r2 - r1) * ratio)
    g = int(g1 + (g2 - g1) * ratio)
    b = int(b1 + (b2 - b1) * ratio)
    return f"#{r:02x}{g:02x}{b:02x}"
