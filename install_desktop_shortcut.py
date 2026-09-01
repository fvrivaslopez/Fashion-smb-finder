#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Creates a double-click shortcut on your Desktop for bonus_goal_allocator.py,
so you don't have to open a code editor or type commands to run it.

Run this ONCE, locally, after cloning the repo:

    python3 install_desktop_shortcut.py

It detects your OS and drops the right kind of shortcut on your Desktop:
  - macOS   -> "Bonus Allocator.command"
  - Linux   -> "Bonus Allocator.desktop"
  - Windows -> "Bonus Allocator.bat"

Nothing is uploaded anywhere; it only writes one small file to your
Desktop folder that points back at this repo.
"""

import os
import platform
import stat
import sys

REPO_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPT_PATH = os.path.join(REPO_DIR, "bonus_goal_allocator.py")
DESKTOP_DIR = os.path.join(os.path.expanduser("~"), "Desktop")


def make_executable(path: str):
    st = os.stat(path)
    os.chmod(path, st.st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)


def install_macos():
    target = os.path.join(DESKTOP_DIR, "Bonus Allocator.command")
    content = f'#!/bin/bash\ncd "{REPO_DIR}"\npython3 "{SCRIPT_PATH}"\n'
    with open(target, "w", encoding="utf-8") as f:
        f.write(content)
    make_executable(target)
    return target, (
        "First double-click: macOS may warn it's from an unidentified developer.\n"
        "  Right-click the icon -> Open -> Open, once, to approve it permanently."
    )


def install_linux():
    target = os.path.join(DESKTOP_DIR, "Bonus Allocator.desktop")
    content = (
        "[Desktop Entry]\n"
        "Type=Application\n"
        "Name=Bonus Allocator\n"
        f'Exec=python3 "{SCRIPT_PATH}"\n'
        "Terminal=true\n"
        "Icon=utilities-terminal\n"
    )
    with open(target, "w", encoding="utf-8") as f:
        f.write(content)
    make_executable(target)
    return target, (
        "First double-click: your file manager may ask to 'Trust/Allow Launching'.\n"
        "  Right-click the icon -> Allow Launching (or Properties -> Permissions -> Executable), once."
    )


def install_windows():
    target = os.path.join(DESKTOP_DIR, "Bonus Allocator.bat")
    content = (
        "@echo off\r\n"
        f'cd /d "{REPO_DIR}"\r\n'
        f'python "{SCRIPT_PATH}"\r\n'
        "pause\r\n"
    )
    with open(target, "w", encoding="utf-8") as f:
        f.write(content)
    return target, "Double-click it like any other program. A console window will open."


def main():
    if not os.path.exists(SCRIPT_PATH):
        print(f"[x] Could not find bonus_goal_allocator.py next to this script ({REPO_DIR}).")
        sys.exit(1)

    if not os.path.isdir(DESKTOP_DIR):
        print(f"[x] No Desktop folder found at {DESKTOP_DIR}.")
        print("    Create one, or edit DESKTOP_DIR in this script, then run it again.")
        sys.exit(1)

    system = platform.system()
    if system == "Darwin":
        target, note = install_macos()
    elif system == "Linux":
        target, note = install_linux()
    elif system == "Windows":
        target, note = install_windows()
    else:
        print(f"[x] Unrecognized OS: {system}. No shortcut created.")
        sys.exit(1)

    print(f"[OK] Shortcut created: {target}")
    print(f"     {note}")
    print("     Double-click it any time you want to run the Bonus & Goal Allocator.")


if __name__ == "__main__":
    main()
