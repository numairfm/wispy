import subprocess

from exceptions import InjectError


class Injector:
    def inject(self, text, mode="paste", send_enter=False):
        try:
            if mode == "paste":
                subprocess.run(
                    ["ydotool", "key", "29:1", "47:1", "47:0", "29:0"],
                    check=True, capture_output=True, timeout=5,
                )
            elif mode == "type":
                subprocess.run(
                    ["ydotool", "type", "-d", "1", "-H", "1", text],
                    check=True, capture_output=True, timeout=60,
                )
            elif mode == "copy":
                pass

            if send_enter:
                subprocess.run(
                    ["ydotool", "key", "28:1", "28:0"],
                    check=True, capture_output=True, timeout=5,
                )
        except FileNotFoundError:
            raise InjectError("ydotool not found — install it")
        except subprocess.CalledProcessError as e:
            raise InjectError(f"Injection failed: {e}")
