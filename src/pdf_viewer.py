import tkinter as tk
from tkinter import messagebox

import os
import time
from bootstrap import fitz, Image, ImageTk, win32api, win32con, win32gui, psutil
import shlex
import subprocess
from loading_json import load_config


# 사용 예시
config = load_config()
scratch_path = config["scratch_path"]


class PDFPageViewer(tk.Frame):
    def __init__(
        self, master, pdf_path, initial_zoom=1.0, canvas_width=400, canvas_height=600
    ):
        super().__init__(master)
        self.doc = fitz.open(pdf_path)
        self.zoom = initial_zoom
        self.page_num = 0
        self.canvas_width = canvas_width
        self.canvas_height = canvas_height

        self.canvas = tk.Canvas(
            self, width=canvas_width, height=canvas_height, bg="white"
        )
        self.v_scroll = tk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.h_scroll = tk.Scrollbar(
            self, orient="horizontal", command=self.canvas.xview
        )
        self.canvas.configure(
            yscrollcommand=self.v_scroll.set, xscrollcommand=self.h_scroll.set
        )
        self.v_scroll.pack(side="right", fill="y")
        self.h_scroll.pack(side="bottom", fill="x")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.img_id = None
        self.photo_img = None
        self.render_page()

        self._drag_data = {"x": 0, "y": 0}
        self.canvas.bind("<ButtonPress-1>", self.on_drag_start)
        self.canvas.bind("<B1-Motion>", self.on_drag_move)
        self.canvas.bind("<ButtonRelease-1>", self.on_drag_end)
        self.canvas.config(cursor="arrow")
        self.canvas.bind_all("<MouseWheel>", self.on_mousewheel_with_ctrl)

    def on_mousewheel_with_ctrl(self, event):
        # Ctrl 키가 눌린 상태에서만 작동 (0x0004는 Control 키 상태 비트)
        if event.state & 0x0004:
            if event.delta > 0:
                self.zoom_in()
            else:
                self.zoom_out()

    def render_page(self):
        page = self.doc.load_page(self.page_num)
        mat = fitz.Matrix(self.zoom, self.zoom)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        img_width, img_height = img.size
        self.photo_img = ImageTk.PhotoImage(img)
        self.canvas.delete("all")
        self.img_id = self.canvas.create_image(0, 0, anchor="nw", image=self.photo_img)
        self.canvas.config(scrollregion=(0, 0, img_width, img_height))

    def on_drag_start(self, event):
        self._drag_data["x"] = event.x
        self._drag_data["y"] = event.y
        self.canvas.config(cursor="fleur")

    def on_drag_end(self, event):
        self.canvas.config(cursor="arrow")

    def on_drag_move(self, event):
        sensitivity = 0.5
        delta_x = (event.x - self._drag_data["x"]) * sensitivity
        delta_y = (event.y - self._drag_data["y"]) * sensitivity
        x0, x1 = self.canvas.xview()
        y0, y1 = self.canvas.yview()
        scrollregion = self.canvas.cget("scrollregion").split()
        if len(scrollregion) == 4:
            x_min, y_min, x_max, y_max = map(int, scrollregion)
        else:
            return
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        scroll_width = x_max - x_min - canvas_width or 1
        scroll_height = y_max - y_min - canvas_height or 1
        abs_x = x0 * scroll_width - delta_x
        abs_y = y0 * scroll_height - delta_y
        abs_x = max(0, min(abs_x, scroll_width))
        abs_y = max(0, min(abs_y, scroll_height))
        self.canvas.xview_moveto(abs_x / scroll_width)
        self.canvas.yview_moveto(abs_y / scroll_height)
        self._drag_data["x"] = event.x
        self._drag_data["y"] = event.y

    def set_page(self, page_num):
        self.page_num = page_num
        self.render_page()

    def zoom_in(self):
        self.zoom *= 1.2
        self.render_page()

    def zoom_out(self):
        self.zoom /= 1.2
        self.render_page()


def find_scratch_window():
    def enum_windows(hwnd, windows):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if "Scratch 2" in title:
                windows.append(hwnd)

    windows = []
    win32gui.EnumWindows(enum_windows, windows)
    return windows[0] if windows else None


def kill_scratch_if_running():
    for proc in psutil.process_iter(["pid", "name"]):
        if "Scratch" in proc.info["name"]:
            try:
                proc.kill()
                print(f"✅ 이전 Scratch 프로세스 종료됨: {proc.info['pid']}")
            except Exception as e:
                print(f"❌ 종료 실패: {e}")


def disable_close_button(hwnd):
    hMenu = win32gui.GetSystemMenu(hwnd, False)
    if hMenu:
        win32gui.EnableMenuItem(
            hMenu, win32con.SC_CLOSE, win32con.MF_BYCOMMAND | win32con.MF_GRAYED
        )


def open_scratch_and_position(sb2_path, x=400, y=0, width=800, height=700):
    sb2_path = os.path.abspath(sb2_path)
    print("🧪 실행 경로:", sb2_path)

    if not os.path.exists(sb2_path):
        messagebox.showerror("Error", f"파일이 존재하지 않습니다:\n{sb2_path}")
        return None

    # 실행 중인 Scratch 종료
    kill_scratch_if_running()
    time.sleep(0.2)

    try:
        cmd = f'"{scratch_path}" "{sb2_path}"'
        proc = subprocess.Popen(shlex.split(cmd))
    except Exception as e:
        messagebox.showerror("Error", f"Scratch 실행 실패: {e}")
        return None

    for _ in range(20):
        hwnd = find_scratch_window()
        if hwnd:
            break
        time.sleep(0.2)
    else:
        messagebox.showwarning("경고", "Scratch 창을 찾지 못했습니다.")
        return None

    win32gui.MoveWindow(hwnd, x, y, width, height, True)
    win32gui.SetWindowPos(
        hwnd, win32con.HWND_TOPMOST, x, y, width, height, win32con.SWP_SHOWWINDOW
    )

    # 💡 Scratch 창 제어: 위치 조정 + 닫기 버튼 비활성화
    win32gui.MoveWindow(hwnd, x, y, width, height, True)
    win32gui.SetWindowPos(
        hwnd, win32con.HWND_TOPMOST, x, y, width, height, win32con.SWP_SHOWWINDOW
    )
    disable_close_button(hwnd)

    return proc
