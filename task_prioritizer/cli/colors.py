"""Terminal colors, TTY detection, output colorization, clipboard."""

from __future__ import annotations

import os
import subprocess
import sys


class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    GOLD = "\033[38;5;220m"
    RED = "\033[38;5;203m"
    GREEN = "\033[38;5;114m"
    CYAN = "\033[38;5;117m"
    MAGENTA = "\033[38;5;177m"
    GRAY = "\033[38;5;245m"
    WHITE = "\033[38;5;255m"
    BLUE = "\033[38;5;111m"
    ORANGE = "\033[38;5;208m"

    @classmethod
    def disable(cls):
        cls.RESET = ""
        cls.BOLD = ""
        cls.DIM = ""
        cls.GOLD = ""
        cls.RED = ""
        cls.GREEN = ""
        cls.CYAN = ""
        cls.MAGENTA = ""
        cls.GRAY = ""
        cls.WHITE = ""
        cls.BLUE = ""
        cls.ORANGE = ""


def supports_color() -> bool:
    if not hasattr(sys.stdout, "isatty"):
        return False
    if not sys.stdout.isatty():
        return False
    return "NO_COLOR" not in os.environ


def colorize_output(output: str) -> str:
    c = Colors
    result = output
    result = result.replace("⭐️", f"{c.GOLD}⭐️{c.RESET}")
    result = result.replace("🚨", f"{c.RED}🚨{c.RESET}")
    result = result.replace("🐢", f"{c.GREEN}🐢{c.RESET}")
    result = result.replace("🥵", f"{c.RED}🥵{c.RESET}")
    result = result.replace("🍭", f"{c.GREEN}🍭{c.RESET}")
    result = result.replace("🎁", f"{c.MAGENTA}🎁{c.RESET}")
    result = result.replace("🗓️", f"{c.CYAN}🗓️{c.RESET}")
    result = result.replace("🎲", f"{c.GRAY}🎲{c.RESET}")
    result = result.replace("🔁", f"{c.CYAN}🔁{c.RESET}")
    return result


def copy_to_clipboard(text: str) -> bool:
    try:
        if sys.platform == "darwin":
            subprocess.run(["pbcopy"], input=text.encode(), check=True)
            return True
        elif sys.platform.startswith("linux"):
            try:
                subprocess.run(["xclip", "-selection", "clipboard"],
                               input=text.encode(), check=True)
                return True
            except FileNotFoundError:
                try:
                    subprocess.run(["xsel", "--clipboard", "--input"],
                                   input=text.encode(), check=True)
                    return True
                except FileNotFoundError:
                    return False
        elif sys.platform == "win32":
            subprocess.run(["clip"], input=text.encode(), check=True, shell=True)
            return True
    except Exception:
        return False
    return False
