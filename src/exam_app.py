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

# 사용 예시
config = load_config()
scratch_path = config["scratch_path"]
root_password = config["root_password"]

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

    x, y, w, h = _rect_for_right_two_thirds(bottom_gap=bottom_gap)
    _move_and_topmost(hwnd, x, y, w, h, topmost=True)

    try:
        rect = win32gui.GetWindowRect(hwnd)
        if _is_offscreen(rect):
            _move_and_topmost(hwnd, x, y, w, h, topmost=True)
    except Exception:
        pass

    disable_close_button(hwnd)
    return True



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

# ★★★ open_scratch_and_position 개선 (기존 함수 대체) ★★★
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

    # 1) PID 기반으로 실제 윈도우 핸들 대기
    hwnd = _wait_for_hwnd_by_pid(proc.pid, timeout=10.0)

    # 2) 폴백: 제목 기반 검색
    if hwnd is None:
        for _ in range(20):
            hwnd = find_scratch_window()
            if hwnd:
                break
            time.sleep(0.2)

    if hwnd is None:
        messagebox.showwarning("경고", "Scratch 창을 찾지 못했습니다.")
        return proc  # 프로세스만 반환(이후 repair 단계에서 재시도)

    # 배치 + 닫기 버튼 비활성화
    _move_and_topmost(hwnd, x, y, width, height, topmost=True)
    disable_close_button(hwnd)

    # 오프스크린 방지 보정
    try:
        rect = win32gui.GetWindowRect(hwnd)
        if _is_offscreen(rect):
            _move_and_topmost(hwnd, x, y, width, height, topmost=True)
    except Exception:
        pass

    return proc


class ExamApp(tk.Tk):
    def __init__(
        self,
        pdf_path,
        sb2_files,
        problem_folder,
        submission_dir,
        exam_round_name="미지정",
        username="미입력",
    ):

        # PyInstaller 환경에서는 sys._MEIPASS 경로 사용
        if hasattr(sys, "_MEIPASS"):
            icon_path = os.path.join(sys._MEIPASS, "app_icon.ico")
        else:
            icon_path = "app_icon.ico"

        try:
            self.iconbitmap(icon_path)
        except Exception as e:
            print(f"[아이콘 오류] {e}")

        self.submission_dir = submission_dir
        self.skipped_pages = []
        self.submitted_pages = []
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
        self.page_start_time = None  # 현재 문제 풀이 시작 시간
        self.time_log = {}  # 문제 번호 → 누적 시간(초)

        # 상태 복구
        if os.path.exists("exam_state.json"):
            with open("exam_state.json", "r") as f:
                try:
                    state = json.load(f)
                    self.submitted_pages = state.get("submitted", [])
                    self.skipped_pages = state.get("skipped", [])
                    self.current_page = state.get("current", 0)
                except:
                    self.current_page = 0
        else:
            self.current_page = 0

        super().__init__()


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

        self.pdf_viewer = PDFPageViewer(self, self.pdf_path, initial_zoom=1)
        self.pdf_viewer.place(relx=0, rely=0, relheight=1, relwidth=1 / 3)

        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        pdf_canvas_width = int(screen_width / 3)
        pdf_canvas_height = screen_height

        self.pdf_viewer = PDFPageViewer(
            self,
            self.pdf_path,
            initial_zoom=1.2,
            canvas_width=pdf_canvas_width,
            canvas_height=pdf_canvas_height,
        )
        self.pdf_viewer.place(relx=0, rely=0, relheight=1, relwidth=1 / 3)

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

        zoom_in_btn = tk.Button(left_group, text="확대 +", command=self.zoom_in, **btn_style)
        zoom_in_btn.pack(side="left", padx=5)

        zoom_out_btn = tk.Button(left_group, text="축소 -", command=self.zoom_out, **btn_style)
        zoom_out_btn.pack(side="left", padx=5)

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


    def rebuild_pdf_viewer(self):
        """PDFPageViewer를 깨끗이 재생성(보이지 않는 이슈 대응)"""
        try:
            # 기존 뷰어 제거
            if hasattr(self, "pdf_viewer") and self.pdf_viewer:
                self.pdf_viewer.destroy()
        except Exception:
            pass

        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        pdf_canvas_width = int(screen_width / 3)
        pdf_canvas_height = screen_height

        # 새로 생성
        self.pdf_viewer = PDFPageViewer(
            self,
            self.pdf_path,
            initial_zoom=1.2,
            canvas_width=pdf_canvas_width,
            canvas_height=pdf_canvas_height,
        )
        self.pdf_viewer.place(relx=0, rely=0, relheight=1, relwidth=1 / 3)
        # 현재 페이지/줌 복원
        self.pdf_viewer.set_page(self.current_page)
        self.update_zoom_label()
        self.update_idletasks()
        # Tk를 잠깐 맨 앞으로 올렸다 내리기(가끔 가려지는 문제 해결)
        try:
            self.attributes("-topmost", True)
            self.after(300, lambda: self.attributes("-topmost", False))
        except Exception:
            pass

    # ExamApp.repair_layout 내 수정
    def repair_layout(self):
        # 1) PDF 복구
        self.rebuild_pdf_viewer()

        # 2) Scratch 재배치 (하단 여백 계산해서 적용)
        gap = self.get_bottom_gap()  # ← 하단 버튼바 높이 기반
        hwnd = find_scratch_window()
        ok = repair_scratch_layout(hwnd, bottom_gap=gap)
        if not ok:
            # 창이 없으면 현재 문제 파일로 재기동(여기도 gap 반영)
            try:
                original_sb2 = self.sb2_files[self.current_page]
                original_name = Path(original_sb2).stem
                if '_문제' in original_name:
                    dest_name = original_name.replace('_문제', '_제출') + '.sb2'
                else:
                    dest_name = original_name + '_제출.sb2'
                dest_path = self.submission_dir / dest_name
                if not dest_path.exists():
                    copy2(original_sb2, dest_path)

                sw = self.winfo_screenwidth()
                sh = self.winfo_screenheight()
                x = int(sw * (1 / 3))
                y = 0
                w = int(sw * (2 / 3))
                h = max(300, sh - gap)  # ← 여기서도 gap 적용
                self.scratch_proc = open_scratch_and_position(str(dest_path), x, y, w, h)
            except Exception as e:
                print(f"[레이아웃 복구] Scratch 재기동 실패: {e}")

        # 3) Tk 올려두기
        try:
            self.lift()
            self.focus_force()
        except Exception:
            pass

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

    def save_state(self):
        with open("exam_state.json", "w") as f:
            json.dump(
                {
                    "submitted": self.submitted_pages,
                    "skipped": self.skipped_pages,
                    "current": self.current_page,
                },
                f,
            )

    def zoom_in(self):
        self.pdf_viewer.zoom_in()
        self.update_zoom_label()

    def zoom_out(self):
        self.pdf_viewer.zoom_out()
        self.update_zoom_label()

    def update_zoom_label(self):
        percent = int(self.pdf_viewer.zoom * 100)
        self.zoom_label.config(text=f"{percent}%")

    def load_page(self, page_num, retry=False):
        if page_num < 0 or page_num >= len(self.sb2_files):
            messagebox.showerror("오류", "잘못된 문제 번호입니다.")
            return

        # ✅ 1. 이전 문제 시간 저장 (가장 먼저 해야 함)
        self.save_time_spent()

        # ✅ 2. 현재 문제 번호 갱신
        self.current_page = page_num

        # ✅ 4. PDF 뷰어, 페이지, 라벨 업데이트
        self.page_label.config(
            text=f"문제 {page_num + 1} / {len(self.sb2_files)}"
            + (" (건너뛴 문제)" if page_num in self.skipped_pages else "")
        )
        self.pdf_viewer.set_page(page_num)
        self.update_zoom_label()

        # ✅ 5. 이전 Scratch 종료
        if self.scratch_proc and self.scratch_proc.poll() is None:
            try:
                self.scratch_proc.terminate()
                self.scratch_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.scratch_proc.kill()

        # ✅ 6. 문제 파일 복사 → Scratch 실행
        original_sb2 = self.sb2_files[page_num]
        original_name = Path(original_sb2).stem
        # dest_name = f"{original_name}_제출.sb2"
        
        if '_문제' in original_name:
            dest_name = original_name.replace('_문제', '_제출') + '.sb2'
        else:
            dest_name = original_name + '_제출.sb2'

        dest_path = self.submission_dir / dest_name


        if not dest_path.exists():
            copy2(original_sb2, dest_path)

        # ExamApp.load_page 내 스크래치 높이 계산 부분 교체
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = int(screen_width * (1 / 3))
        y = 0
        gap = self.get_bottom_gap()         # ← 추가
        w = int(screen_width * (2 / 3))
        h = max(300, screen_height - gap)   # ← gap 반영
        print(f"🧪 Scratch 위치 및 크기: x={x}, y={y}, w={w}, h={h} (하단 여백 {gap}px 반영)")
        self.scratch_proc = open_scratch_and_position(str(dest_path), x, y, w, h)

        # ✅ 3. 다시풀기가 아닌 경우에만 시간 시작
        # if not retry:
        self.page_start_time = time.time()

        # ✅ 7. 내비게이션 버튼 업데이트
        self.update_nav_buttons()

    def save_time_spent(self):
        if self.page_start_time is not None:
            elapsed = time.time() - self.page_start_time
            self.time_log[self.current_page] = (
                self.time_log.get(self.current_page, 0) + elapsed
            )
            self.page_start_time = None

    def retry_page(self):
        # 1) 시간 누적
        self.save_time_spent()

        # 2) 현재 문제 다시 로드(Scratch 파일 재오픈/교체 포함)
        self.load_page(self.current_page, retry=True)

        # 3) 레이아웃 강제 복구(여기서 PDF 재생성 + Scratch 재배치)
        self.repair_layout()

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
                self.scratch_proc.terminate()
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
        total = len(self.sb2_files)
        done = len(self.submitted_pages)
        skipped = len(self.skipped_pages)
        self.update_meta_with_time()

        messagebox.showinfo(
            "시험 종료", f"총 문제 수: {total}\n제출: {done}\n건너뜀: {skipped}"
        )
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
