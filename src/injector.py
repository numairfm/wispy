import subprocess

from exceptions import InjectError


class Injector:
    def inject(self, text, mode="paste", send_enter=False):
        try:
            if mode == "paste":
                # Send Ctrl+V with 12ms key delay so Wayland processes modifiers
                subprocess.run(
                    ["ydotool", "key", "-d", "12", "29:1", "47:1", "47:0", "29:0"],
                    check=True, capture_output=True, timeout=5,
                )
            elif mode == "copy":
                pass

            if send_enter:
                subprocess.run(
                    ["ydotool", "key", "-d", "12", "28:1", "28:0"],
                    check=True, capture_output=True, timeout=5,
                )
        except FileNotFoundError:
            raise InjectError("ydotool not found — install it")
        except subprocess.CalledProcessError as e:
            raise InjectError(f"Injection failed: {e}")

