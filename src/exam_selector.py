import tkinter as tk
from tkinter import ttk

import os
from exam_app import ExamApp
from tkinter import simpledialog
import json
from pathlib import Path
from datetime import datetime
from tkinter import messagebox


class ExamSelector(tk.Tk):
    def __init__(self, base_path):
        super().__init__()
        self.base_path = base_path
        print(f"ExamSelector self.base_path: {self.base_path}")

        self.submission_meta_path = None  # ✅ 제출본 경로 저장용

        # 창 크기
        window_width = 480
        window_height = 620

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
            messagebox.showerror("오류", f"재채점 중 오류 발생: {e}")

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

        self.folder_name = f"{username}_{exam_round_name}_{today}"
        self.submission_dir = self.user_home / "Desktop" / self.folder_name
        self.submission_dir.mkdir(parents=True, exist_ok=True)

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
