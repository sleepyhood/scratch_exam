# bootstrap.py
import subprocess
import sys

REQUIRED_PACKAGES = [
    ("PyMuPDF", "fitz"),
    ("Pillow", "PIL"),
    ("pywin32", "win32gui"),
    ("psutil", None),
    ("pyautogui", None),
    ("jinja2", None),
    ("pandas", None)
]

for pkg_name, import_name in REQUIRED_PACKAGES:
    if import_name is None:
        import_name = pkg_name
    try:
        __import__(import_name)
        print(f"✅ '{pkg_name}' 패키지 설치 확인됨.")
    except ImportError:
        print(f"📦 '{pkg_name}' 패키지를 설치합니다...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", pkg_name])
        except subprocess.CalledProcessError as e:
            print(f"❌ 설치 실패: {pkg_name} → {e}")

# 이제 나머지 외장 모듈 import
import fitz
from PIL import Image, ImageTk
import win32con
import win32api 
import win32gui
import pyautogui
import psutil
from shutil import copy2
import jinja2
import pandas