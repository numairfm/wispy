import subprocess

from exceptions import InjectError


class Injector:
    def inject(self, text):
        try:
            subprocess.run(
                ["ydotool", "type", "-d", "1", "-H", "1", text],
                check=True, capture_output=True, timeout=60,
            )
        except FileNotFoundError:
            raise InjectError("ydotool not found — install it")
        except subprocess.CalledProcessError as e:
            raise InjectError(f"Type failed: {e}")

    def copy(self, text):
        from PyQt6.QtWidgets import QApplication
        QApplication.clipboard().setText(text)
