import tkinter as tk
from tkinter import messagebox

import subprocess
import time
import os
import sys
from pathlib import Path
import shlex
import getpass
from tkinter import simpledialog
import threading
from datetime import datetime
import json
from pdf_viewer import PDFPageViewer
import bootstrap  # 설치용

# 외부 패키지는 직접 import
from PIL import Image, ImageTk
from shutil import copy2
import win32gui, win32api, win32con
import psutil

from loading_json import load_config
import fitz  # 외부 모듈은 직접 import
# 파일 상단 import 구역에 추가
import win32process
import win32con
# 사용 예시
config = load_config()
scratch_path = config["scratch_path"]
root_password = config["root_password"]
icon_path = config.get("app_icon_path")        
# def _kill_proc_tree(proc: subprocess.Popen):
#     try:
#         p = psutil.Process(proc.pid)
#         for child in p.children(recursive=True):
#             try: child.kill()
#             except: pass
#         try: p.kill()
#         except: pass
#     except Exception:
#         pass
def _kill_proc_tree(proc: subprocess.Popen):
    try:
        p = psutil.Process(proc.pid)
        for child in p.children(recursive=True):
            try: child.kill()
            except: pass
        try: p.kill()
        except: pass
    except Exception:
        pass


def _restore_and_place(hwnd, x, y, w, h, topmost=True):
    try:
        # 최소화/최대화 상태면 먼저 복원
        if win32gui.IsIconic(hwnd) or win32gui.IsZoomed(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            time.sleep(0.05)
        win32gui.ShowWindow(hwnd, win32con.SW_SHOWNOACTIVATE)
    except Exception:
        pass
    _move_and_topmost(hwnd, x, y, w, h, topmost=topmost)
        
# exam_app.py 유틸 영역에 추가
def _enum_windows_for_pid_tree(root_pid):
    pids = {root_pid}
    try:
        for c in psutil.Process(root_pid).children(recursive=True):
            pids.add(c.pid)
    except: pass

    wins = []
    def _cb(hwnd, acc):
        if win32gui.IsWindowVisible(hwnd):
            try:
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                if pid in pids:
                    acc.append(hwnd)
            except: pass
    win32gui.EnumWindows(_cb, wins)
    return wins

def _pick_main_window_for_pid(root_pid, timeout=15.0):
    """부모/자식 PID 전체에서 '가장 큰 영역'의 창을 메인 창으로 간주"""
    start = time.time()
    best = None; best_area = 0
    while time.time() - start < timeout:
        wins = _enum_windows_for_pid_tree(root_pid)
        for w in wins:
            try:
                l,t,r,b = win32gui.GetWindowRect(w)
                area = max(0, r-l) * max(0, b-t)
                title = (win32gui.GetWindowText(w) or "")
                # 제목에 Scratch가 있는 창을 우선 가중치
                if ("Scratch" in title) or ("스크래치" in title):
                    area *= 2
                if area > best_area:
                    best = w; best_area = area
            except: pass
        if best_area > 600*400:   # 충분히 큰 창이면 조기 확정
            break
        time.sleep(0.2)
    return best


# ★★★ find_scratch_window 개선 + 보조 유틸들 추가 (기존 함수 대체/추가) ★★★

def _enum_windows_for_pid(target_pid):
    found = []
    def _cb(hwnd, acc):
        if win32gui.IsWindowVisible(hwnd):
            try:
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                if pid == target_pid:
                    acc.append(hwnd)
            except Exception:
                pass
    win32gui.EnumWindows(_cb, found)
    return found

def _wait_for_hwnd_by_pid(pid, timeout=10.0):
    start = time.time()
    hwnd = None
    while time.time() - start < timeout:
        wins = _enum_windows_for_pid(pid)
        if wins:
            # 최상위 창 하나만 리턴
            return wins[0]
        time.sleep(0.2)
    return None

def find_scratch_window():
    """제목 기반(폴백) Scratch 창 탐색"""
    def enum_windows(hwnd, windows):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd) or ""
            # 다양한 제목 케이스 대응
            if ("Scratch" in title) or ("스크래치" in title):
                windows.append(hwnd)
    windows = []
    win32gui.EnumWindows(enum_windows, windows)
    return windows[0] if windows else None

def _get_screen_size():
    sw = win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
    sh = win32api.GetSystemMetrics(win32con.SM_CYSCREEN)
    return sw, sh

def _is_offscreen(rect):
    # rect: (left, top, right, bottom)
    sw, sh = _get_screen_size()
    l, t, r, b = rect
    # 화면과 전혀 교차하지 않으면 오프스크린으로 간주
    if r <= 0 or b <= 0 or l >= sw or t >= sh:
        return True
    return False

# 기존 _rect_for_right_two_thirds()를 아래처럼 교체
def _rect_for_right_two_thirds(bottom_gap=0, min_height=300):
    sw, sh = _get_screen_size()
    left = int(sw / 3)
    width = sw - left
    height = max(min_height, sh - bottom_gap)  # 하단 여백만큼 줄이기
    return left, 0, width, height

def _move_and_topmost(hwnd, x, y, w, h, topmost=True):
    win32gui.MoveWindow(hwnd, x, y, w, h, True)
    win32gui.SetWindowPos(
        hwnd,
        win32con.HWND_TOPMOST if topmost else win32con.HWND_NOTOPMOST,
        x, y, w, h,
        win32con.SWP_SHOWWINDOW
    )

# 기존 repair_scratch_layout을 아래처럼 교체(시그니처 변경)
def repair_scratch_layout(hwnd=None, bottom_gap=0):
    """Scratch 창을 오른쪽 2/3로 재배치(하단 안전 여백 반영)."""
    if hwnd is None:
        hwnd = find_scratch_window()
    if not hwnd:
        return False

    # x, y, w, h = _rect_for_right_two_thirds(bottom_gap=bottom_gap)
    # _move_and_topmost(hwnd, x, y, w, h, topmost=True)

    x, y, w, h = _rect_for_right_two_thirds(bottom_gap=bottom_gap)
    _restore_and_place(hwnd, x, y, w, h, topmost=True)

    try:
        rect = win32gui.GetWindowRect(hwnd)
        if _is_offscreen(rect):
            _move_and_topmost(hwnd, x, y, w, h, topmost=True)
    except Exception:
        pass

    disable_close_button(hwnd)
    return True



def _norm(p):
    try:
        return os.path.normcase(os.path.normpath(p or ""))
    except Exception:
        return p or ""

def _looks_like_scratch_proc(p: psutil.Process) -> bool:
    """scratch_path와 정확히 일치하거나, 자식 트리 내 창 제목이 Scratch인 AIR 런처만 허용"""
    try:
        exe = _norm(p.exe())
        tgt = _norm(scratch_path)
        if exe and tgt and exe == tgt:
            return True

        # 보조 규칙: AIR 런처/자식인데 'Scratch' 메인창을 실제로 가지고 있으면만 허용
        name = (p.name() or "").lower()
        if name in ("adobe air.exe", "adobe air", "scratch 2.exe", "scratch.exe"):
            for hwnd in _enum_windows_for_pid_tree(p.pid):
                title = (win32gui.GetWindowText(hwnd) or "")
                if ("Scratch 2" in title) or ("Offline Editor" in title) or ("스크래치" in title):
                    return True
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass
    return False

def kill_scratch_if_running():
    victims = []
    for p in psutil.process_iter(["pid", "name", "exe"]):
        try:
            if _looks_like_scratch_proc(p):
                victims.append(p)
        except Exception:
            pass

    for p in victims:
        try:
            for c in p.children(recursive=True):
                try: c.kill()
                except: pass
            p.kill()
        except Exception:
            pass



def disable_close_button(hwnd):
    hMenu = win32gui.GetSystemMenu(hwnd, False)
    if hMenu:
        win32gui.EnableMenuItem(
            hMenu, win32con.SC_CLOSE, win32con.MF_BYCOMMAND | win32con.MF_GRAYED
        )

# ★★★ open_scratch_and_position 개선 (기존 함수 대체) ★★★
def open_scratch_and_position(sb2_path, x=400, y=0, width=800, height=700):
    sb2_path = os.path.abspath(sb2_path)
    if not os.path.exists(sb2_path):
        messagebox.showerror("Error", f"파일이 존재하지 않습니다:\n{sb2_path}")
        return None, None

    # 1) 완전 정리
    kill_scratch_if_running()
    time.sleep(0.2)

    # 2) 실행
    cmd = f'"{scratch_path}" "{sb2_path}"'
    proc = subprocess.Popen(shlex.split(cmd))

    # 3) 메인 창 대기(부모+자식 PID 전체에서 가장 큰 창)
    hwnd = _pick_main_window_for_pid(proc.pid, timeout=18.0)

    if hwnd is None:
        messagebox.showwarning("경고", "Scratch 메인 창을 찾지 못했습니다.")
        return proc, None

    # 4) 메인 창만 배치/제어 (스플래시는 무시)
    # 기존
    # _move_and_topmost(hwnd, x, y, width, height, topmost=True)
    # disable_close_button(hwnd)

    # 변경
    _restore_and_place(hwnd, x, y, width, height, topmost=True)
    disable_close_button(hwnd)

    try:
        rect = win32gui.GetWindowRect(hwnd)
        if _is_offscreen(rect):
            _move_and_topmost(hwnd, x, y, width, height, topmost=True)
    except: pass

    print(f"[SCRATCH] started pid={proc.pid}, hwnd={hwnd}")

    return proc, hwnd


class ExamApp(tk.Tk):
    def __init__(
        self,
        pdf_path,
        sb2_files,
        problem_folder,
        submission_dir,
        exam_round_name="미지정",
        username="미입력",
        load_state=True,   # ✅ 추가: 상태 복구 여부
        pdf_page_indices=None,

    ):

        # PyInstaller 환경에서는 sys._MEIPASS 경로 사용
        # if hasattr(sys, "_MEIPASS"):
        #     icon_path = os.path.join(sys._MEIPASS, "app_icon.ico")
        # else:
        #     icon_path = "app_icon.ico"

        self._launching_scratch = False
        self.submission_dir = submission_dir
        self.skipped_pages = []
        self.submitted_pages = []
        if pdf_page_indices is None:
            self.pdf_page_indices = list(range(len(sb2_files)))
        else:
            self.pdf_page_indices = [int(idx) for idx in pdf_page_indices]
            if len(self.pdf_page_indices) != len(sb2_files):
                raise ValueError("pdf_page_indices 길이가 sb2_files와 일치해야 합니다.")
        
        self.PDF_MIN_ZOOM = 0.8     # 80%
        self.PDF_MAX_ZOOM = 2.0     # 200%
        self.PDF_DEFAULT_ZOOM = 1.2 # 120% (현재 초기값과 일치)
        # self.user_home = Path.home()
        # today = datetime.now().strftime("%Y%m%d")

        # folder_name = f"{username}_{exam_round_name}_{today}"
        # self.submission_dir = self.user_home / "Desktop" / folder_name
        # self.submission_dir.mkdir(parents=True, exist_ok=True)

        # # 메타 저장 호출
        # # 문제 폴더는 exam_selector에서 찾았다면
        # parent_folder = os.path.dirname(problem_folder)
        # answer_folder = os.path.join(
        #     parent_folder, [f for f in os.listdir(parent_folder) if "정답" in f][0]
        # )

        # self.save_meta(pdf_path, sb2_files, answer_folder)

        # 시간 기록
        # self.page_start_time = None  # 현재 문제 풀이 시작 시간
        # self.time_log = {}  # 문제 번호 → 누적 시간(초)

        # # 상태 복구
        # if os.path.exists("exam_state.json"):
        #     with open("exam_state.json", "r") as f:
        #         try:
        #             state = json.load(f)
        #             self.submitted_pages = state.get("submitted", [])
        #             self.skipped_pages = state.get("skipped", [])
        #             self.current_page = state.get("current", 0)
        #         except:
        #             self.current_page = 0
        # else:
        #     self.current_page = 0

                # 시간 기록
        self.page_start_time = None  # 현재 문제 풀이 시작 시간
        self.time_log = {}  # 문제 번호 → 누적 시간(초)

        # ✅ 상태 복구: 제출 폴더 안의 exam_state.json 사용 (시험 재개용)
        self.state_path = Path(self.submission_dir) / "exam_state.json"
        self.current_page = 0


        # 🔧 여기에서 load_state 옵션 체크
        if load_state and self.state_path.exists():
            try:
                with open(self.state_path, "r", encoding="utf-8") as f:
                    state = json.load(f)
                self.submitted_pages = state.get("submitted", [])
                self.skipped_pages = state.get("skipped", [])
                self.current_page = state.get("current", 0)

                # time_log은 {문제번호(int): 시간(초)} 형태로 복구
                raw_log = state.get("time_log", {})
                self.time_log = {int(k): float(v) for k, v in raw_log.items()}
                print(f"[STATE] 복구 완료: current={self.current_page}, "
                      f"submitted={self.submitted_pages}, skipped={self.skipped_pages}")
            except Exception as e:
                print(f"[STATE] 복구 실패: {e}")
                # 실패하면 그냥 초기 상태로 두고 진행
                self.submitted_pages = []
                self.skipped_pages = []
                self.current_page = 0
                self.time_log = {}
        else:
            self.current_page = 0


        # 1) 반드시 가장 먼저 Tk 초기화
        super().__init__()

        # 2) 아이콘 경로 결정
        # if hasattr(sys, "_MEIPASS"):
        #     icon_path = os.path.join(sys._MEIPASS, "app_icon.ico")
        # else:
        #     # 실행 파일과 같은 폴더 기준 (원하면 절대경로로)
        #     icon_path = os.path.join(os.path.dirname(__file__), "app_icon.ico")

        print(f"[아이콘 경로] {icon_path}")

        # 3) 아이콘 적용 (Windows .ico)
        try:
            self.iconbitmap(icon_path)          # 또는 self.iconbitmap(default=icon_path)
        except Exception as e:
            print(f"[아이콘 오류] {e}")
        

        # ✅ 문제지 PDF 복사: 이름에 날짜와 학생 이름을 포함
        try:
            today = datetime.now().strftime("%Y%m%d")
            pdf_filename = f"{username}_{exam_round_name}_{today}_문제지.pdf"
            pdf_copy_path = self.submission_dir / pdf_filename

            if not pdf_copy_path.exists():
                copy2(pdf_path, pdf_copy_path)
                print(f"✅ 문제지 PDF 복사 완료: {pdf_copy_path}")
            else:
                print("⚠ 이미 PDF가 복사되어 있습니다:", pdf_copy_path)

            self.pdf_copied_path = pdf_copy_path  # 나중에 meta 저장 등에서 사용 가능

        except Exception as e:
            print(f"❌ PDF 복사 중 오류 발생: {e}")


        # ✅ 원본 문제 파일들과 정답 파일들도 함께 복사
        try:
            # 문제 폴더 경로 생성
            problem_dest_dir = self.submission_dir / "문제"
            problem_dest_dir.mkdir(parents=True, exist_ok=True)

            for sb2_path in sb2_files:
                sb2_name = Path(sb2_path).name
                dest_path = problem_dest_dir / sb2_name
                if not dest_path.exists():
                    copy2(sb2_path, dest_path)
                    print(f"📄 문제 복사: {sb2_name}")

            # 정답 폴더 경로 추정 및 생성
            parent = Path(problem_folder).parent
            answer_folder = next(
                (parent / d for d in os.listdir(parent) if "정답" in d),
                None,
            )

            if answer_folder and answer_folder.exists():
                answer_dest_dir = self.submission_dir / "정답"
                answer_dest_dir.mkdir(parents=True, exist_ok=True)

                for file in os.listdir(answer_folder):
                    if file.endswith(".sb2"):
                        src = answer_folder / file
                        dst = answer_dest_dir / file
                        if not dst.exists():
                            copy2(src, dst)
                            print(f"📄 정답 복사: {file}")
            else:
                print("⚠ 정답 폴더를 찾을 수 없습니다.")

        except Exception as e:
            print(f"❌ 문제/정답 복사 중 오류: {e}")


        self.title("자격증 시험 시뮬레이터")
        self.geometry("1200x800")

        self.protocol("WM_DELETE_WINDOW", self.on_close_attempt)

        self.pdf_path = pdf_path
        self.sb2_files = sb2_files
        # print(os.path.exists(sb2_files[0]))
        self.scratch_proc = None
        self.scratch_hwnd = None

        # self.pdf_viewer = PDFPageViewer(self, self.pdf_path, initial_zoom=1)
        # self.pdf_viewer.place(relx=0, rely=0, relheight=1, relwidth=1 / 3)

        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        pdf_canvas_width = int(screen_width / 3)
        pdf_canvas_height = screen_height

        # 아래 한 세트만 남기세요
        self.pdf_viewer = PDFPageViewer(
            self,
            self.pdf_path,
            initial_zoom=self.PDF_DEFAULT_ZOOM,
            canvas_width=int(self.winfo_screenwidth()/3),
            canvas_height=self.winfo_screenheight(),
        )
        self.pdf_viewer.place(relx=0, rely=0, relheight=1, relwidth=1/3)


        self.right_frame = tk.Frame(self, bg="lightgray")
        self.right_frame.place(relx=1 / 3, rely=0, relheight=1, relwidth=2 / 3)

        nav_frame = tk.Frame(self.right_frame, bg="lightgray")
        nav_frame.pack(pady=20)

        # __init__ 내부의 bottom_frame 생성 부분을 아래처럼 변경
        self.bottom_frame = tk.Frame(self.right_frame, bg="lightgray")
        self.bottom_frame.pack(side="bottom", fill="x", pady=10)

        # zoom_in_btn = tk.Button(bottom_frame, text="확대 +", command=self.zoom_in)
        # zoom_in_btn.pack(side="left", padx=5)

        # zoom_out_btn = tk.Button(bottom_frame, text="축소 -", command=self.zoom_out)
        # zoom_out_btn.pack(side="left", padx=5)

        # self.zoom_label = tk.Label(bottom_frame, text="100%", bg="lightgray")
        # self.zoom_label.pack(side="left", padx=10)

        # self.page_label = tk.Label(
        #     bottom_frame, text="", bg="lightgray", font=("Arial", 12)
        # )
        # self.page_label.pack(side="left", padx=10)

        # # 시간
        # # 기존 page_label 아래에 추가
        # self.time_label = tk.Label(
        #     bottom_frame, text="풀이시간: 0분 0초", bg="lightgray", font=("Arial", 12)
        # )
        # self.time_label.pack(side="left", padx=10)

        # self.retry_btn = tk.Button(
        #     bottom_frame, text="다시 풀기", command=self.retry_page
        # )
        # self.retry_btn.pack(side="left", padx=10)

        # self.skip_btn = tk.Button(
        #     bottom_frame, text="건너 뛰기", command=self.skip_page
        # )
        # self.skip_btn.pack(side="left", padx=10)

        # self.next_btn = tk.Button(
        #     bottom_frame, text="다음 문제", command=self.confirm_saved_before_submit
        # )
        # self.next_btn.pack(side="left", padx=10)

        left_group = tk.Frame(self.bottom_frame, bg="lightgray")

        left_group.pack(side="left")

        btn_style = {
            "bg": "#007BFF",            # 파란색
            "fg": "white",              # 흰색 글씨
            "activebackground": "#0056b3",  # 눌렀을 때 어두운 파란색
            "activeforeground": "white",
            "font": ("맑은 고딕", 10, "bold"),
            "relief": "flat",           # 테두리 평평하게 (선택 사항)
            "width": 10                 # 버튼 너비 설정 (선택 사항)
        }

        self.zoom_in_btn  = tk.Button(left_group, text="확대 +", command=self.zoom_in,  **btn_style)
        self.zoom_out_btn = tk.Button(left_group, text="축소 -", command=self.zoom_out, **btn_style)
        self.zoom_in_btn.pack(side="left", padx=5)
        self.zoom_out_btn.pack(side="left", padx=5)

        self.reset_btn = tk.Button(left_group, text="초기화/정렬", command=self.reset_layout, **btn_style)
        self.reset_btn.pack(side="left", padx=5)


        self.zoom_label = tk.Label(left_group, text="100%", bg="lightgray")
        self.zoom_label.pack(side="left", padx=10)

        self.page_label = tk.Label(
            left_group, text="", bg="lightgray", font=("Arial", 12)
        )
        self.page_label.pack(side="left", padx=10)

        self.time_label = tk.Label(
            left_group, text="풀이시간: 0분 0초", bg="lightgray", font=("Arial", 12)
        )
        self.time_label.pack(side="left", padx=10)

        # 오른쪽 그룹 (다시 풀기, 건너뛰기, 다음 문제)
        right_group = tk.Frame(self.bottom_frame, bg="lightgray")
        right_group.pack(side="right")

        self.retry_btn = tk.Button(
            right_group, text="다시 풀기", command=self.confirm_retry, **btn_style
        )
        self.retry_btn.pack(side="left", padx=10)

        self.skip_btn = tk.Button(
            right_group, text="건너 뛰기", command=self.confirm_skip, **btn_style
        )
        self.skip_btn.pack(side="left", padx=10)

        self.next_btn = tk.Button(
            right_group, text="다음 문제", command=self.confirm_saved_before_submit, **btn_style
        )
        self.next_btn.pack(side="left", padx=10)

        self.info_label = tk.Label(
            self.right_frame,
            text="스크래치 문제 풀이 공간",
            font=("Arial", 14),
            bg="lightgray",
        )
        self.info_label.pack(pady=30)

        self.load_page(self.current_page)
        # self.state("zoomed")
        self.attributes("-fullscreen", True)

        self.bind("<F11>", lambda e: self.repair_layout())

        self.enable_admin_exit()
        self.update_time_label()

    def _settle_scratch(self, x, y, w, h, attempt=0, max_attempts=10):
        # 프로세스가 살아있을 때만
        if not (self.scratch_proc and self.scratch_proc.poll() is None):
            return
        hwnd = _pick_main_window_for_pid(self.scratch_proc.pid, timeout=1.0)
        if hwnd:
            # 메인창 판단: 면적이 충분히 크거나(예: 600x400 이상)
            # 현재 목표 크기/위치와 차이가 나면 다시 배치
            try:
                l, t, r, b = win32gui.GetWindowRect(hwnd)
                area = max(0, r-l) * max(0, b-t)
                need_resize = (
                    abs(l - x) > 2 or abs(t - y) > 2 or abs((r-l) - w) > 2 or abs((b-t) - h) > 2
                )
                if area < 600*400 or need_resize:
                    _restore_and_place(hwnd, x, y, w, h, topmost=True)
                    disable_close_button(hwnd)
                self.scratch_hwnd = hwnd
            except Exception as e:
                print(f"[SCRATCH] settle check failed: {e}")
        if attempt < max_attempts:
            # 0.25초 간격으로 10회 정도 재확인 (총 ~2.5초)
            self.after(250, lambda: self._settle_scratch(x, y, w, h, attempt+1, max_attempts))



    def _raise_scratch_on_top(self, x=None, y=None, w=None, h=None):
        try:
            if self.scratch_proc and self.scratch_proc.poll() is None:
                # 메인 창 재탐색(스플래시/보조창 회피)
                hwnd = _pick_main_window_for_pid(self.scratch_proc.pid, timeout=1.2)
                if hwnd:
                    self.scratch_hwnd = hwnd
                    if None not in (x,y,w,h):
                        _move_and_topmost(hwnd, x, y, w, h, topmost=True)
                    else:
                        # 위치가 이미 계산돼 있으면 단순 TopMost 재적용
                        l,t,r,b = win32gui.GetWindowRect(hwnd)
                        _move_and_topmost(hwnd, l, t, r-l, b-t, topmost=True)
                    disable_close_button(hwnd)
        except Exception as e:
            print(f"[SCRATCH] raise/topmost failed: {e}")

    def _cull_other_scratch_instances(self):
        """현재 self.scratch_proc 외의 Scratch 인스턴스가 있으면 종료(보조 실행 제거)"""
        try:
            if not (self.scratch_proc and self.scratch_proc.poll() is None):
                return
            keep_pid = self.scratch_proc.pid

            victims = []
            for p in psutil.process_iter(["pid","name","exe"]):
                try:
                    if not _looks_like_scratch_proc(p):  # 우리가 판별한 Scratch만
                        continue
                    if p.pid == keep_pid:
                        continue
                    # keep_pid의 자식(헬퍼)은 살려둠
                    if p.pid in {c.pid for c in psutil.Process(keep_pid).children(recursive=True)}:
                        continue
                    victims.append(p)
                except Exception:
                    pass

            for p in victims:
                try:
                    for c in p.children(recursive=True):
                        try: c.kill()
                        except: pass
                    p.kill()
                    print(f"[SCRATCH] culled extra instance pid={p.pid}")
                except Exception:
                    pass
        except Exception as e:
            print(f"[SCRATCH] cull error: {e}")


    # ExamApp 클래스 안에 추가
    def get_bottom_gap(self, fallback=60):
        """
        오른쪽 영역 하단 버튼 바의 실제 높이에 기반해
        스크래치 창 높이에서 빼줄 안전 여백을 계산.
        """
        try:
            self.update_idletasks()
            h = self.bottom_frame.winfo_height()
            # 버튼이 0으로 나오면 아직 레이아웃 전일 수 있으니 폴백 사용
            gap = max(fallback, h + 16)  # 약간의 패딩
            return gap
        except Exception:
            return fallback

    def update_zoom_buttons(self):
        try:
            z = float(getattr(self.pdf_viewer, "zoom", self.PDF_DEFAULT_ZOOM))
        except Exception:
            z = self.PDF_DEFAULT_ZOOM
        # 약간의 오차 허용치
        eps = 1e-3
        if hasattr(self, "zoom_in_btn"):
            self.zoom_in_btn.config(state=("disabled" if z >= self.PDF_MAX_ZOOM - eps else "normal"))
        if hasattr(self, "zoom_out_btn"):
            self.zoom_out_btn.config(state=("disabled" if z <= self.PDF_MIN_ZOOM + eps else "normal"))


    def rebuild_pdf_viewer(self, zoom=None):
        """PDFPageViewer를 깨끗이 재생성(보이지 않는 이슈 대응) + 원하는 배율로 시작"""
        try:
            if hasattr(self, "pdf_viewer") and self.pdf_viewer:
                self.pdf_viewer.destroy()
        except Exception:
            pass

        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        pdf_canvas_width = int(screen_width / 3)

        # 요청 줌이 없으면 기본값, 있으면 상하한으로 클램프
        if zoom is None:
            z = self.PDF_DEFAULT_ZOOM
        else:
            z = max(self.PDF_MIN_ZOOM, min(self.PDF_MAX_ZOOM, float(zoom)))

        self.pdf_viewer = PDFPageViewer(
            self,
            self.pdf_path,
            initial_zoom=z,
            canvas_width=pdf_canvas_width,
            canvas_height=screen_height,
        )
        self.pdf_viewer.place(relx=0, rely=0, relheight=1, relwidth=1/3)
        self.pdf_viewer.set_page(self.current_page)
        self.update_zoom_label()
        self.update_idletasks()
        # try:
        #     self.attributes("-topmost", True)
        #     self.after(300, lambda: self.attributes("-topmost", False))
        # except Exception:
        #     pass

        # 버튼 활성/비활성 반영
        self.update_zoom_buttons()


    # ExamApp.repair_layout 내 수정
    # def repair_layout(self):
    #     # 1) PDF 복구
    #     self.rebuild_pdf_viewer()

    #     # 2) Scratch 재배치 (하단 여백 계산해서 적용)
    #     gap = self.get_bottom_gap()  # ← 하단 버튼바 높이 기반
    #     hwnd = find_scratch_window()
    #     ok = repair_scratch_layout(hwnd, bottom_gap=gap)
    #     if not ok:
    #         # 창이 없으면 현재 문제 파일로 재기동(여기도 gap 반영)
    #         try:
    #             original_sb2 = self.sb2_files[self.current_page]
    #             original_name = Path(original_sb2).stem
    #             if '_문제' in original_name:
    #                 dest_name = original_name.replace('_문제', '_제출') + '.sb2'
    #             else:
    #                 dest_name = original_name + '_제출.sb2'
    #             dest_path = self.submission_dir / dest_name
    #             if not dest_path.exists():
    #                 copy2(original_sb2, dest_path)

    #             sw = self.winfo_screenwidth()
    #             sh = self.winfo_screenheight()
    #             x = int(sw * (1 / 3))
    #             y = 0
    #             w = int(sw * (2 / 3))
    #             h = max(300, sh - gap)  # ← 여기서도 gap 적용
    #             self.scratch_proc = open_scratch_and_position(str(dest_path), x, y, w, h)
    #         except Exception as e:
    #             print(f"[레이아웃 복구] Scratch 재기동 실패: {e}")

    #     # 3) Tk 올려두기
    #     try:
    #         self.lift()
    #         self.focus_force()
    #     except Exception:
    #         pass

    def repair_layout(self):
        self.rebuild_pdf_viewer()
        gap = self.get_bottom_gap()

        # 1) 살아있는 메인 창 찾기
        hwnd = None
        if self.scratch_hwnd and win32gui.IsWindow(self.scratch_hwnd):
            hwnd = self.scratch_hwnd
        elif self.scratch_proc and self.scratch_proc.poll() is None:
            hwnd = _pick_main_window_for_pid(self.scratch_proc.pid, timeout=2.0)

        # 2) 찾으면 그 창만 재배치, 못 찾으면 잠깐 뒤 재시도 (재실행 금지)
        if hwnd:
            if repair_scratch_layout(hwnd, bottom_gap=gap):
                self.scratch_hwnd = hwnd
        else:
            self.after(400, self.repair_layout)
            return

        try:
            self.lift(); self.focus_force()
        except: pass


    def update_time_label(self):
        base = self.time_log.get(self.current_page, 0)

        if self.page_start_time is not None:
            elapsed = base + (time.time() - self.page_start_time)
        else:
            elapsed = base
        minutes = int(elapsed) // 60
        seconds = int(elapsed) % 60
        self.time_label.config(text=f"풀이시간: {minutes}분 {seconds}초")
        self.after(1000, self.update_time_label)

    def enable_admin_exit(self):
        # 비밀 단축키 등록
        self.bind("<F12>", lambda e: self.prompt_password_exit())

    def prompt_password_exit(self):
        self.attributes("-topmost", True)  # 먼저 자기 자신을 위로
        pw = simpledialog.askstring(
            "관리자 종료", "종료 비밀번호를 입력하세요:", show="*", parent=self
        )
        # self.attributes("-topmost", False)  # 다시 원래대로

        if pw == root_password:  # 원하는 비밀번호로 바꾸세요
            if messagebox.askyesno("종료 확인", "정말 프로그램을 종료하시겠습니까?"):
                self.quit_app()
        else:
            messagebox.showwarning("실패", "비밀번호가 틀렸습니다.")

    def on_close_attempt(self):
        messagebox.showwarning("종료 차단", "시험 도중에는 창을 닫을 수 없습니다.")

    # def confirm_saved_before_submit(self):
    #     self.attributes("-topmost", True)  # 먼저 자기 자신을 위로
    #     answer = messagebox.askyesno("저장 확인", "Scratch에서 저장하셨나요?")
    #     if answer:
    #         self.submit_and_next()
    #     else:
    #         messagebox.showinfo(
    #             "알림", "먼저 Scratch에서 저장을 완료한 후 다음 문제로 넘어가세요."
    #         )
    #     self.attributes("-topmost", False)  # 다시 원래대로

    def confirm_retry(self):
        self.attributes("-topmost", True)
        answer = messagebox.askyesno(
            "다시 풀기 확인",
            "현재 문제는 저장되지 않습니다.\n정말 문제를 다시 푸시겠습니까?",
        )
        if answer:
            self.retry_page()
        else:
            messagebox.showinfo("취소됨", "문제 다시 풀기가 취소되었습니다.")
        self.attributes("-topmost", False)

    def confirm_skip(self):
        self.attributes("-topmost", True)
        answer = messagebox.askyesno(
            "건너뛰기 확인",
            "이 문제는 저장되지 않고 건너뜁니다.\n마지막 문제 이후 다시 등장합니다.\n정말 건너뛰시겠습니까?",
        )
        if answer:
            self.skip_page()
        else:
            messagebox.showinfo("취소됨", "문제 건너뛰기가 취소되었습니다.")
        self.attributes("-topmost", False)

    def confirm_saved_before_submit(self):
        self.attributes("-topmost", True)
        answer = messagebox.askyesno(
            "다음 문제로 이동",
            "⚠ 현재 문제를 저장하셨나요?\n(저장하지 않으면 복구할 수 없습니다)\n\n이후에는 현재 문제로 돌아올 수 없습니다.\n\n계속하시겠습니까?",
        )
        if answer:
            self.submit_and_next()
        else:
            messagebox.showinfo("알림", "Scratch에서 저장한 후, 다시 시도하세요.")
        self.attributes("-topmost", False)

    # def save_state(self):
    #     with open("exam_state.json", "w") as f:
    #         json.dump(
    #             {
    #                 "submitted": self.submitted_pages,
    #                 "skipped": self.skipped_pages,
    #                 "current": self.current_page,
    #             },
    #             f,
    #         )

    def save_state(self):
        """현재 풀이 상태를 제출 폴더 안 exam_state.json에 저장 (시험 재개용)."""
        if not hasattr(self, "state_path"):
            self.state_path = Path(self.submission_dir) / "exam_state.json"

        payload = {
            "submitted": self.submitted_pages,
            "skipped": self.skipped_pages,
            "current": self.current_page,
            "time_log": self.time_log,
        }
        try:
            with open(self.state_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            # print(f"[STATE] 저장: {self.state_path}")
        except Exception as e:
            print(f"[STATE] 저장 실패: {e}")


    def reset_layout(self):
        """PDF 배율을 기본값으로 초기화하고, 스크래치 창을 안전하게 재배치"""
        # PDF 배율 초기화
        self.rebuild_pdf_viewer(self.PDF_DEFAULT_ZOOM)

        # 스크래치 재배치(기존 F11 동작)
        gap = self.get_bottom_gap()
        hwnd = None
        if self.scratch_hwnd and win32gui.IsWindow(self.scratch_hwnd):
            hwnd = self.scratch_hwnd
        elif self.scratch_proc and self.scratch_proc.poll() is None:
            hwnd = _pick_main_window_for_pid(self.scratch_proc.pid, timeout=2.0)

        if hwnd:
            if repair_scratch_layout(hwnd, bottom_gap=gap):
                self.scratch_hwnd = hwnd
        else:
            # 잠시 후 한 번 더 재시도(재실행 금지)
            self.after(400, self.repair_layout)
        self.after(400, lambda: self._raise_scratch_on_top())



    def zoom_in(self):
        z = float(getattr(self.pdf_viewer, "zoom", self.PDF_DEFAULT_ZOOM))
        if z >= self.PDF_MAX_ZOOM - 1e-3:
            # 이미 최대 → 버튼만 갱신
            self.update_zoom_buttons()
            return
        self.pdf_viewer.zoom_in()
        # 한 번 더 확인(뷰어 내부 스텝으로 초과할 수 있음)
        if getattr(self.pdf_viewer, "zoom", z) > self.PDF_MAX_ZOOM:
            self.rebuild_pdf_viewer(self.PDF_MAX_ZOOM)
        self.update_zoom_label()
        self.update_zoom_buttons()

    def zoom_out(self):
        z = float(getattr(self.pdf_viewer, "zoom", self.PDF_DEFAULT_ZOOM))
        if z <= self.PDF_MIN_ZOOM + 1e-3:
            self.update_zoom_buttons()
            return
        self.pdf_viewer.zoom_out()
        if getattr(self.pdf_viewer, "zoom", z) < self.PDF_MIN_ZOOM:
            self.rebuild_pdf_viewer(self.PDF_MIN_ZOOM)
        self.update_zoom_label()
        self.update_zoom_buttons()


    def update_zoom_label(self):
        percent = int(self.pdf_viewer.zoom * 100)
        self.zoom_label.config(text=f"{percent}%")


    def load_page(self, page_num, retry=False):
        if self._launching_scratch:
            print("[SCRATCH] launch in progress → skip")
            return
        self._launching_scratch = True        

        try:
            if page_num < 0 or page_num >= len(self.sb2_files):
                messagebox.showerror("오류", "잘못된 문제 번호입니다.")
                return

            # 1) 이전 문제 시간 저장
            self.save_time_spent()

            # 2) 현재 문제 번호 갱신
            self.current_page = page_num

            # 3) PDF/라벨 업데이트
            pdf_page_num = self.pdf_page_indices[page_num]
            self.page_label.config(
                text=f"문제 {page_num + 1} / {len(self.sb2_files)}"
                + (" (건너뛴 문제)" if page_num in self.skipped_pages else "")
            )
            self.pdf_viewer.set_page(pdf_page_num)
            self.update_zoom_label()

            # 4) 이전 Scratch 종료 (항상 '실행 전에')
            if self.scratch_proc and self.scratch_proc.poll() is None:
                _kill_proc_tree(self.scratch_proc)
                self.scratch_proc = None
                self.scratch_hwnd = None
                time.sleep(0.2)

            # 5) 문제 파일 복사 → 제출본 경로 계산
            original_sb2 = self.sb2_files[page_num]
            original_name = Path(original_sb2).stem
            if '_문제' in original_name:
                dest_name = original_name.replace('_문제', '_제출') + '.sb2'
            else:
                dest_name = original_name + '_제출.sb2'
            dest_path = self.submission_dir / dest_name

            if not dest_path.exists():
                copy2(original_sb2, dest_path)

            # 6) 배치 좌표 계산
            screen_width = self.winfo_screenwidth()
            screen_height = self.winfo_screenheight()
            gap = self.get_bottom_gap()
            x = int(screen_width * (1/3))
            y = 0
            w = int(screen_width * (2/3))
            h = max(300, screen_height - gap)
            print(f"🧪 Scratch 위치 및 크기: x={x}, y={y}, w={w}, h={h} (하단 여백 {gap}px)")

            # 7) Scratch '한 번만' 실행 (튜플로 받기!)
            self.scratch_proc, self.scratch_hwnd = open_scratch_and_position(
                str(dest_path), x, y, w, h
            )
            
            # 7.5) 실행 직후 ~2.5초 동안 메인창 등장/크기변경을 감시하며 재배치
            self.after(500, lambda: self._settle_scratch(x, y, w, h))

            # 8) 시간 시작 + 버튼 상태
            self.page_start_time = time.time()
            self.update_nav_buttons()

            # 9) ✅ 시험 상태 저장 (시험 재개 대비)
            self.save_state()
        finally:
            self._launching_scratch = False


    def save_time_spent(self):
        if self.page_start_time is not None:
            elapsed = time.time() - self.page_start_time
            self.time_log[self.current_page] = (
                self.time_log.get(self.current_page, 0) + elapsed
            )
            self.page_start_time = None

    def retry_page(self):
        self.save_time_spent()
        self.load_page(self.current_page, retry=True)
        self.after(300, self.repair_layout)  # 창이 완전히 뜬 뒤 재배치

    def skip_page(self):
        self.save_time_spent()  # 🔄 이 줄을 먼저!

        if self.current_page not in self.skipped_pages:
            self.skipped_pages.append(self.current_page)
        next_page = self.get_next_available_page()
        if next_page is not None:
            self.load_page(next_page)
        else:
            messagebox.showinfo(
                "알림", "더 이상 풀 문제 없습니다. 건너뛴 문제를 다시 풀어주세요."
            )

    def submit_and_next(self):
        if self.current_page not in self.submitted_pages:
            self.submitted_pages.append(self.current_page)
        if self.current_page in self.skipped_pages:
            self.skipped_pages.remove(self.current_page)

        self.save_time_spent()
        next_page = self.get_next_available_page()

        if next_page is not None:
            self.load_page(next_page)
        else:
            self.end_exam_ui()
            self.show_result_summary()

    def get_next_available_page(self):
        total = len(self.sb2_files)

        # 🔹 1단계: 아직 제출도, 건너뛰지도 않은 문제 먼저
        for i in range(total):
            if i not in self.submitted_pages and i not in self.skipped_pages:
                return i

        # 🔹 2단계: 그다음에 건너뛴 문제들 다시 돌아감
        for i in self.skipped_pages:
            if i not in self.submitted_pages:
                return i

        return None

    def end_exam_ui(self):
        # Scratch 종료
        if self.scratch_proc and self.scratch_proc.poll() is None:
            try:
                _kill_proc_tree(self.scratch_proc)
            except:
                pass

        self.page_label.config(text="시험이 완료되었습니다.")
        self.info_label.config(
            text="모든 문제 풀이가 끝났습니다.\n종료하려면 '종료하기' 버튼을 누르세요."
        )

        self.retry_btn.config(state="disabled")
        self.skip_btn.config(state="disabled")
        self.next_btn.config(text="종료하기", command=self.quit_app)

    def quit_app(self):
        # 종료 직전에 마지막 시간/상태 저장
        try:
            self.save_time_spent()
            self.save_state()
        except Exception as e:
            print(f"[STATE] 종료 전 저장 실패: {e}")

        self.destroy()  # Tkinter 종료

    def update_nav_buttons(self):
        total = len(self.sb2_files)
        self.retry_btn.config(state="normal")
        self.skip_btn.config(
            state=(
                "normal"
                if self.current_page not in self.submitted_pages
                else "disabled"
            )
        )
        self.next_btn.config(
            state=(
                "normal"
                if self.current_page not in self.submitted_pages
                else "disabled"
            )
        )
        # 종료 조건일 경우 버튼 변경
        if self.get_next_available_page() is None:
            self.next_btn.config(text="종료하기", command=self.quit_app)
        else:
            self.next_btn.config(
                text="다음 문제", command=self.confirm_saved_before_submit
            )

    def show_result_summary(self):
        from pathlib import Path
        # 채점 쪽 에러가 나도 시험창이 터지지 않게 try로 감싸기
        total = len(self.sb2_files)
        done = len(self.submitted_pages)
        skipped = len(self.skipped_pages)

        # 1) 시간 정보 meta.json에 기록
        self.update_meta_with_time()

        # 2) 시험 종료와 동시에 채점 + HTML 리포트 생성/열기
        try:
            from grader import grade_from_meta
            from html_report import save_results_as_html

            meta_path = Path(self.submission_dir) / "meta.json"
            results = grade_from_meta(meta_path)

            # 재채점 버튼에서는 regrade_mode=True로 쓰고 있으니,
            # 여기서는 일반 종료 모드로 호출
            try:
                save_results_as_html(results, meta_path=meta_path, regrade_mode=False)
            except TypeError:
                # 혹시 regrade_mode 인자를 안 받는 버전일 수도 있으니 호환 코드
                save_results_as_html(results, meta_path)
        except Exception as e:
            print(f"[시험 종료 채점/리포트 오류] {e}")

        # 3) 요약 팝업
        messagebox.showinfo(
            "시험 종료", f"총 문제 수: {total}\n제출: {done}\n건너뜀: {skipped}"
        )

    # def show_result_summary(self):
    #     total = len(self.sb2_files)
    #     done = len(self.submitted_pages)
    #     skipped = len(self.skipped_pages)
    #     self.update_meta_with_time()

    #     messagebox.showinfo(
    #         "시험 종료", f"총 문제 수: {total}\n제출: {done}\n건너뜀: {skipped}"
    #     )
        # self.save_time_log()

    # def save_time_log(self):
    #     meta_path = self.meta_path  # 이미 self.meta_path 속성이 있다면 사용
    #     if not meta_path:
    #         print("⚠ meta_path가 설정되지 않았습니다.")
    #         return

    #     try:
    #         with open(meta_path, "r", encoding="utf-8") as f:
    #             meta = json.load(f)

    #         # 예시: 풀이 시간 로그를 meta에 넣기
    #         meta["log_saved"] = True  # 단순히 저장됐다는 표시

    #         with open(meta_path, "w", encoding="utf-8") as f:
    #             json.dump(meta, f, ensure_ascii=False, indent=2)

    #         print("✅ 풀이 시간 로그 저장 완료")

    #     except Exception as e:
    #         print(f"❌ save_time_log 오류: {e}")

    def update_meta_with_time(self):
        meta_path = self.submission_dir / "meta.json"
        if not meta_path.exists():
            return

        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)

        readable = {
            f"문제{idx+1}": round(sec, 2) for idx, sec in sorted(self.time_log.items())
        }

        meta["time_log"] = readable
        meta["total_time"] = round(sum(self.time_log.values()), 2)

        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=4, ensure_ascii=False)
