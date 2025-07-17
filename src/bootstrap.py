# bootstrap.py
import subprocess
import sys


def install_if_missing(package_name, import_name=None):
    if import_name is None:
        import_name = package_name
    try:
        __import__(import_name)
    except ImportError:
        print(f"[설치 필요] '{package_name}' 패키지를 설치합니다...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package_name])


# bootstrap.py 내부에서 이처럼 깔끔하게 관리
REQUIRED_PACKAGES = [
    ("PyMuPDF", "fitz"),
    ("Pillow", "PIL"),
    ("pywin32", "win32gui"),
    ("psutil", None),
    ("pyautogui", None),
    ("jinja2", None),
]

for pkg_name, import_name in REQUIRED_PACKAGES:
    install_if_missing(pkg_name, import_name)


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
