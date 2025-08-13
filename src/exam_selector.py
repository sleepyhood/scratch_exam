import tkinter as tk
from tkinter import ttk

import os
from exam_app import ExamApp
from tkinter import simpledialog
import json
from pathlib import Path
from datetime import datetime
from tkinter import messagebox
import traceback

from itertools import count
# (파일 상단 import 근처에 추가)
from tkinter import filedialog  # ✅ 전역 import
import uuid, socket, zipfile, shutil  # ✅ 번들 전송에 사용

from loading_json import load_config
from pathlib import Path
from typing import Optional



# 사용 예시
# 어딘가에서 ExamSelector 만들 때:
config = load_config()
default_exam_folder = Path(config["default_exam_folder_toDCT2"])
report_inbox = config.get("report_inbox", r"\\DCT2\Desktop\DCT2_공유폴더\ExamReports\incoming")


# ✅ config 저장 헬퍼 (외부 save_config 없을 때도 동작하도록)
def _fallback_save_config_to_userfile(cfg: dict):
    try:
        p = Path.home() / ".scratch_exam_config.json"
        with open(p, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def _save_config(self):
    if self._save_config_func:
        try:
            self._save_config_func(self.config)
            return
        except Exception:
            pass
    _fallback_save_config_to_userfile(self.config)

def _open_settings_menu(self):
    menu = tk.Menu(self, tearoff=0)
    menu.add_command(label="시험 폴더 경로 설정…", command=self._pick_exam_base_path)
    menu.add_command(label="문제 신고 / 관리자 전송…", command=self._report_issue_dialog)
    menu.add_separator()
    menu.add_command(label="공유 드롭박스 폴더 설정…", command=self._pick_share_dir)
    try:
        x = self.winfo_pointerx(); y = self.winfo_pointery()
        menu.tk_popup(x, y)
    finally:
        menu.grab_release()

def _pick_exam_base_path(self):
    new_base = filedialog.askdirectory(title="시험 폴더 최상위 경로 선택")
    if not new_base:
        return
    self.base_path = new_base
    # ✅ 전역 config에도 반영
    self.config["default_exam_folder_toDCT2"] = new_base
    self._save_config()

    # 라디오버튼 UI 갱신
    for w in self.exam_type_frame.winfo_children():
        w.destroy()
    for exam_type in self.get_exam_types():
        rb = tk.Radiobutton(
            self.exam_type_frame,
            text=exam_type,
            variable=self.exam_type_var,
            value=exam_type,
            font=("맑은 고딕", 13),
            indicatoron=False, width=25, padx=10, pady=5,
            relief="raised", bd=2, selectcolor="#cce5ff",
            command=self.update_exam_rounds,
        )
        rb.pack(anchor="w", pady=3)
    messagebox.showinfo("완료", "시험 폴더 경로가 변경되었습니다.")


def _pick_share_dir(self):
    new_share = filedialog.askdirectory(title="메인PC 공유 드롭박스 폴더 선택")
    if not new_share:
        return
    self.share_dir = new_share
    # 🔁 여기만 변경
    self.config["report_inbox"] = new_share      # 이전: self.config["share_dir"] = new_share
    self._save_config()
    messagebox.showinfo("완료", f"공유 폴더가 변경되었습니다.\n{self.share_dir}")

def _unique_prefix(self, exam_id, student_id):
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    host = socket.gethostname()
    rid = uuid.uuid4().hex[:8]
    return f"{ts}_exam-{exam_id}_stu-{student_id}_{host}_{rid}"

def _send_issue_bundle(self, meta_path: Path, result_html: Optional[Path], sb2_paths, anomalies_text: str):
    share = Path(self.share_dir)
    share.mkdir(parents=True, exist_ok=True)

    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)
    exam_id = meta.get("exam_round_name", "unknown")
    student_id = meta.get("username", "unknown")
    prefix = self._unique_prefix(exam_id, student_id)

    # JSON 요약
    payload = {
        "exam_id": exam_id,
        "student_id": student_id,
        "hostname": socket.gethostname(),
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "anomalies": (anomalies_text or "").strip(),
        "app": "ExamSelector",
        "submission_dir": meta.get("submission_dir"),
    }
    tmp_json = share / f"{prefix}.json.tmp"
    fin_json = share / f"{prefix}.json"
    with open(tmp_json, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    os.replace(tmp_json, fin_json)  # 원자적 커밋

    # ZIP 번들
    tmp_zip = share / f"{prefix}.zip.tmp"
    fin_zip = share / f"{prefix}.zip"
    with zipfile.ZipFile(tmp_zip, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.write(meta_path, arcname="meta.json")
        if result_html and result_html.exists():
            z.write(result_html, arcname=result_html.name)
        for p in sb2_paths or []:
            pth = Path(p)
            if pth.exists():
                z.write(pth, arcname=f"sb2/{pth.name}")
    os.replace(tmp_zip, fin_zip)
def _report_issue_dialog(self):
    # meta.json 찾기 (진행 중 시험이면 self.submission_meta_path 사용)
    meta_path = None
    if self.submission_meta_path and Path(self.submission_meta_path).exists():
        meta_path = Path(self.submission_meta_path)
    else:
        pick = filedialog.askopenfilename(title="meta.json 선택", filetypes=[("JSON", "*.json")])
        if pick:
            meta_path = Path(pick)

    if not meta_path or not meta_path.exists():
        messagebox.showerror("오류", "meta.json을 찾지 못했습니다.")
        return

    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)
    subdir = Path(meta.get("submission_dir", "") or meta_path.parent)
    result_html = subdir / "시험결과.html"
    sb2_paths = meta.get("sb2_files", [])

    desc = simpledialog.askstring("문제 신고", "오류/이상 내용을 간단히 적어주세요.")
    if desc is None:
        return

    try:
        self._send_issue_bundle(meta_path, result_html, sb2_paths, desc)
        messagebox.showinfo("완료", "관리자에게 전송되었습니다.")
    except Exception as e:
        messagebox.showerror("오류", f"전송 중 오류: {e}")




class ExamSelector(tk.Tk):
    def __init__(self, base_path):
        super().__init__()
        self.base_path = base_path
        print(f"ExamSelector self.base_path: {self.base_path}")

        # ✅ 추가: 공유 드롭박스(메인PC) 기본 경로 및 설정 로드

        self.share_dir = report_inbox         # ✅ 문제신고 전송 경로
        # ✅ 추가: 전역 config 참조 & 저장함수 자리(없으면 None)
        self.config = config
        self._save_config_func = None

        self.submission_meta_path = None  # ✅ 제출본 경로 저장용

        # 창 크기
        window_width = 480
        window_height = 620

        # ✅ 추가: 우상단 설정 버튼
        topbar = tk.Frame(self)
        topbar.pack(fill="x", pady=(6, 0))
        settings_btn = tk.Button(
            topbar, text="⚙ 설정", command=self._open_settings_menu,
            font=("맑은 고딕", 10, "bold")
        )
        settings_btn.pack(side="right", padx=8)

        # 화면 해상도 기준 중앙 위치 계산
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = int((screen_width - window_width) / 2)
        y = int((screen_height - window_height) / 2)

        # 창 위치 설정
        self.geometry(f"{window_width}x{window_height}+{x}+{y}")
        self.title("시험 등급 선택")

        self.exam_type_var = tk.StringVar()
        self.exam_round_var = tk.StringVar()

        tk.Label(
            self, text="시험 등급을 선택하세요", font=("맑은 고딕", 13, "bold")
        ).pack(pady=10)

        self.exam_type_var = tk.StringVar()
        self.exam_type_frame = tk.Frame(self)
        self.exam_type_frame.pack()

        for exam_type in self.get_exam_types():
            rb = tk.Radiobutton(
                self.exam_type_frame,
                text=exam_type,
                variable=self.exam_type_var,
                value=exam_type,
                font=("맑은 고딕", 13),
                indicatoron=False,  # ✅ 원 대신 버튼처럼 표시
                width=25,
                padx=10,
                pady=5,
                relief="raised",
                bd=2,
                selectcolor="#cce5ff",  # 선택되었을 때 배경
                command=self.update_exam_rounds,
            )
            rb.pack(anchor="w", pady=3)

        tk.Label(
            self, text="시험 회차를 선택하세요", font=("맑은 고딕", 13, "bold")
        ).pack(pady=10)

        # style.configure(
        #     "Custom.TCombobox", font=("맑은 고딕", 13), padding=5  # 입력창 폰트
        # )
        self.exam_round_combo = ttk.Combobox(
            self,
            textvariable=self.exam_round_var,
            state="disabled",
            font=("맑은 고딕", 12),
            width=30,
        )
        self.exam_round_combo.pack(pady=5)

        btn_style = {
            "bg": "#007BFF",  # 파란색
            "fg": "white",  # 흰 글씨
            "font": ("맑은 고딕", 11, "bold"),  # ✅ 폰트 크기 ↑
            "activebackground": "#0056b3",
            "activeforeground": "white",
            "disabledforeground": "#999999",  # 비활성 상태에서 글자색
            "width": 20,
        }

        self.start_btn = tk.Button(
            self,
            text="시험 시작",
            state="disabled",
            command=self.confirm_start,
            **btn_style,
            cursor="hand2",  # 👈 마우스 오버 시 손모양
        )
        self.start_btn.pack(pady=20)

        regrade_btn_style = btn_style.copy()
        regrade_btn_style["bg"] = "#28a745"  # 녹색
        regrade_btn_style["activebackground"] = "#1e7e34"

        self.regrade_btn = tk.Button(
            self,
            text="재채점 실행",
            command=self.select_folder_for_regrade,
            **regrade_btn_style,
        )
        self.regrade_btn.pack(pady=10)

        # self.label = tk.Label(self, text="시험 등급을 선택하세요", font=("Arial", 16))
        # self.label.pack(pady=20)

        # self.button_frame = tk.Frame(self)
        # self.button_frame.pack()

        # self.show_exam_types()

        # def set_icon(self):



    def select_folder_for_regrade(self):
        from tkinter import filedialog
        from grader import regrade_submission_folder

        folder = filedialog.askdirectory(title="제출 폴더 선택")
        if not folder:
            return

        try:
            regrade_submission_folder(folder)
            messagebox.showinfo("완료", "재채점이 완료되었습니다.")
        except Exception as e:
            tb = traceback.format_exc()
            messagebox.showerror("오류", f"재채점 중 오류 발생: {e}\n{tb}")

    def get_exam_types(self):
        return [
            folder
            for folder in os.listdir(self.base_path)
            if os.path.isdir(os.path.join(self.base_path, folder))
        ]

    def update_exam_rounds(self, event=None):
        selected_type = self.exam_type_var.get()
        exam_type_path = os.path.join(self.base_path, selected_type)
        rounds = [
            folder
            for folder in os.listdir(exam_type_path)
            if os.path.isdir(os.path.join(exam_type_path, folder))
        ]
        self.exam_round_combo["values"] = rounds
        self.exam_round_combo["state"] = "readonly"
        self.exam_round_combo.set("")

        def enable_start(e):
            self.start_btn["state"] = "normal"

        self.exam_round_combo.bind("<<ComboboxSelected>>", enable_start)

    def confirm_start(self):
        exam_type = self.exam_type_var.get()
        exam_round = self.exam_round_var.get()
        if exam_type and exam_round:
            selected_path = os.path.join(self.base_path, exam_type, exam_round)
            self.start_exam(selected_path)

    def clear_widgets(self):
        # 기존 위젯 모두 삭제
        for widget in self.button_frame.winfo_children():
            widget.destroy()

    def show_exam_types(self):
        self.label.config(text="시험 등급을 선택하세요")
        self.clear_widgets()

        for folder in os.listdir(self.base_path):
            folder_path = os.path.join(self.base_path, folder)
            if os.path.isdir(folder_path):
                btn = tk.Button(
                    self.button_frame,
                    text=folder,
                    width=30,
                    command=lambda f=folder_path: self.show_exam_rounds(f),
                )
                btn.pack(pady=5)

    def show_exam_rounds(self, exam_type_path):
        self.label.config(text="시험 회차를 선택하세요")
        self.clear_widgets()

        for folder in os.listdir(exam_type_path):
            folder_path = os.path.join(exam_type_path, folder)
            if os.path.isdir(folder_path):
                btn = tk.Button(
                    self.button_frame,
                    text=folder,
                    width=30,
                    command=lambda f=folder_path: self.start_exam(f),
                    font=("맑은 고딕", 13),
                )
                btn.pack(pady=5)

        # 🔙 뒤로가기 버튼 추가
        back_btn = tk.Button(
            self.button_frame,
            text="← 뒤로가기",
            width=30,
            fg="blue",
            command=self.show_exam_types,
        )
        back_btn.pack(pady=20)

    def start_exam(self, selected_path):
        sb2_files = []

        # 회차명 = 폴더 이름
        exam_round_name = os.path.basename(selected_path)

        # ✅ 사용자 이름 입력받기
        self.withdraw()

        username = simpledialog.askstring("이름 입력", "수험자 이름을 입력하세요:")
        self.deiconify()

        if not username:
            username = "미입력"

        # ✅ 존재 여부 초기화
        pdf_path = None
        problem_folder = None
        answer_folder = None

        # PDF 찾기
        for file in os.listdir(selected_path):
            if file.endswith(".pdf"):
                pdf_path = os.path.join(selected_path, file)

        # 문제 폴더 찾기
        problem_folder = next(
            os.path.join(selected_path, f)
            for f in os.listdir(selected_path)
            if "문제" in f and os.path.isdir(os.path.join(selected_path, f))
        )
        sb2_files = [
            os.path.join(problem_folder, f)
            for f in sorted(os.listdir(problem_folder))
            if f.endswith(".sb2")
        ]

        # 문제 폴더는 exam_selector에서 찾았다면
        parent_folder = os.path.dirname(problem_folder)
        answer_folder = os.path.join(
            parent_folder, [f for f in os.listdir(parent_folder) if "정답" in f][0]
        )

        # ✅ 누락된 리소스 있을 경우 경고 후 되돌아가기
        missing = []
        if not pdf_path:
            missing.append("PDF 파일")
        if not problem_folder:
            missing.append("문제 폴더")
        if not answer_folder:
            missing.append("정답 폴더")

        if missing:
            messagebox.showerror(
                "리소스 누락",
                f"다음 항목이 누락되었습니다: {', '.join(missing)}\n시험 폴더를 다시 선택해주세요.",
            )
            return  # 함수 종료 → 초기 selector화면 유지됨

        # 메타 저장 호출
        self.user_home = Path.home()
        today = datetime.now().strftime("%Y%m%d")



        base_folder_name = f"{username}_{exam_round_name}_{today}"
        submission_dir = self.user_home / "Desktop" / base_folder_name

        for i in count(1):
            if not submission_dir.exists():
                break
            submission_dir = self.user_home / "Desktop" / f"{base_folder_name}_{i}"

        self.folder_name = submission_dir.name
        self.submission_dir = submission_dir
        self.submission_dir.mkdir(parents=True, exist_ok=False)



        self.submission_meta_path = self.submission_dir / "meta.json"

        self.save_meta(pdf_path, sb2_files, answer_folder)

        self.destroy()
        app = ExamApp(
            pdf_path,
            sb2_files,
            problem_folder,
            submission_dir=self.submission_dir,
            exam_round_name=exam_round_name,
            username=username,
        )
        # self.destroy()
        # app = ExamApp(pdf_path, sb2_files)
        # folder_name = os.path.basename(selected_path)
        # app = ExamApp(pdf_path, sb2_files, exam_round_name=folder_name)

        app.mainloop()

    def save_meta(self, pdf_path, sb2_files, answer_folder):
        meta = {
            "exam_round_name": self.submission_dir.name.split("_")[1],
            "username": self.submission_dir.name.split("_")[0],
            "date": self.submission_dir.name.split("_")[2],
            "pdf_path": str(pdf_path),
            "sb2_files": [str(f) for f in sb2_files],
            "answer_folder": str(answer_folder),
            "submission_dir": str(self.submission_dir),
        }
        meta_path = self.submission_dir / "meta.json"
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=4, ensure_ascii=False)


# ---- 클래스 바깥 전역에 정의된 함수들을 ExamSelector 메서드로 바인딩 ----
ExamSelector._open_settings_menu   = _open_settings_menu
ExamSelector._pick_exam_base_path  = _pick_exam_base_path
ExamSelector._pick_share_dir       = _pick_share_dir
ExamSelector._unique_prefix        = _unique_prefix
ExamSelector._send_issue_bundle    = _send_issue_bundle
ExamSelector._report_issue_dialog  = _report_issue_dialog
ExamSelector._save_config          = _save_config
