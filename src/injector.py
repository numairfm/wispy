import re
import subprocess

from exceptions import InjectError


def check_stop_keyword(text, keyword=""):
    """If text contains a stop keyword near the end, return (stripped_text, True).
    Keywords can be comma-separated. Otherwise return (text, False)."""
    if not keyword:
        return text, False
    for kw in [k.strip() for k in keyword.split(",") if k.strip()]:
        escaped = re.escape(kw)
        # match keyword near end, allowing punctuation and short trailing speech
        gap = r'[\s.!?,;:\-]*'
        pattern = r'(?:[.!?,]\s+|and\s+)?' + escaped + gap + r'(?:\w+' + gap + r'){0,5}\s*$'
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            stripped = text[:m.start()].rstrip().rstrip(',.').strip()
            return stripped, True
    return text, False


class Injector:
    def inject(self, text, press_enter=False):
        try:
            subprocess.run(
                ["ydotool", "type", "-d", "1", "-H", "1", text],
                check=True, capture_output=True, timeout=60,
            )
            if press_enter:
                subprocess.run(
                    ["ydotool", "key", "Return"],
                    check=True, capture_output=True, timeout=10,
                )
        except FileNotFoundError:
            raise InjectError("ydotool not found — install it")
        except subprocess.CalledProcessError as e:
            raise InjectError(f"Type failed: {e}")

    def copy(self, text):
        from PyQt6.QtWidgets import QApplication
        QApplication.clipboard().setText(text)
