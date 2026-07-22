import re
import subprocess

from exceptions import InjectError

# Matches send-command phrases at the very END of transcribed text.
# Only matches standalone "send it/that/the message" — NOT "do not send it"
# or other mid-sentence uses. Allows preceding sentence boundary or just spaces.
_SEND_RE = re.compile(
    r'(?:[.!?,]\s+|and\s+)?'       # optional sentence boundary or "and"
    r'(?<!\bdo not )'               # negative lookbehind: not "do not send"
    r'(?<!\bdon\'t )'               # negative lookbehind: not "don't send"
    r'(?<!\bdont )'                 # negative lookbehind: not "dont send"
    r'send\s+'
    r'(?:it|that|the\s+(?:message|prompt|text|command))'
    r'\s*\.?\s*$',
    re.IGNORECASE,
)


def check_send_command(text):
    """If text ends with a send-command phrase, return (stripped_text, True).
    Otherwise return (text, False)."""
    m = _SEND_RE.search(text)
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
