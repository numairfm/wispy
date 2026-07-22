import re
import subprocess

from exceptions import InjectError


def check_stop_keyword(text, keyword="send it"):
    """If text ends with the stop keyword, return (stripped_text, True).
    Otherwise return (text, False). The keyword is matched case-insensitively
    only at the very end of the text, not mid-sentence."""
    if not keyword:
        return text, False
    # Escape the keyword for regex, then match at end with optional punctuation
    escaped = re.escape(keyword)
    pattern = r'(?:[.!?,]\s+|and\s+)?' + escaped + r'\s*\.?\s*$'
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
