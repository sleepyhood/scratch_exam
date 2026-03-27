import tkinter as tk
from tkinter import ttk
from tkinter import font as tkfont

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


def _extract_retry_candidates(meta_path):
    """meta.json을 기준으로 오답 문제 목록과 매핑 진단 정보를 반환한다."""
    from grader import grade_from_meta, normalize_name

    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)

    all_sb2 = meta.get("sb2_files") or []
    if not all_sb2:
        raise ValueError("meta.json에 sb2_files 정보가 없습니다.")

    results = grade_from_meta(meta_path)

    wrong_keys = []
    for row in results:
        if row.get("정답여부") == "O":
            continue

        submit_path = row.get("제출파일경로")
        if not submit_path:
            continue

        wrong_keys.append(normalize_name(Path(submit_path).stem))

    unique_wrong_keys = []
    seen = set()
    for key in wrong_keys:
        if key in seen:
            continue
        seen.add(key)
        unique_wrong_keys.append(key)

    sb2_by_key = {}
    duplicate_problem_keys = set()
    for sb2_path in all_sb2:
        problem_key = normalize_name(Path(sb2_path).stem)
        if problem_key in sb2_by_key:
            duplicate_problem_keys.add(problem_key)
            continue
        sb2_by_key[problem_key] = sb2_path

    matched_sb2 = []
    matched_original_indices = []
    unmatched_keys = []
    for key in unique_wrong_keys:
        matched = sb2_by_key.get(key)
        if matched:
            matched_sb2.append(matched)
            matched_original_indices.append(all_sb2.index(matched))
        else:
            unmatched_keys.append(key)

    diagnostics = {
        "results": results,
        "wrong_keys": unique_wrong_keys,
        "unmatched_keys": unmatched_keys,
        "duplicate_problem_keys": sorted(duplicate_problem_keys),
        "all_sb2_count": len(all_sb2),
        "matched_original_indices": matched_original_indices,
    }
    return meta, matched_sb2, diagnostics


def _safe_path_component(text, fallback="untitled"):
    cleaned = "".join("_" if ch in '<>:"/\\|?*' else ch for ch in str(text or ""))
    cleaned = cleaned.strip().rstrip(".")
    return cleaned or fallback


def _create_wrong_retry_session(meta_path, meta, wrong_sb2, diagnostics):
    """오답 재도전용 새 제출 세션 폴더와 meta.json을 만든다."""
    source_submission_dir = Path(meta.get("submission_dir") or meta_path.parent)
    if not source_submission_dir.exists():
        raise ValueError(f"submission_dir 경로가 존재하지 않습니다:\n{source_submission_dir}")
    if not wrong_sb2:
        raise ValueError("오답 재도전 대상으로 만들 문제가 없습니다.")

    username = meta.get("username", "미입력")
    exam_round_name = meta.get("exam_round_name", "미지정")
    date_str = datetime.now().strftime("%Y%m%d")
    safe_username = _safe_path_component(username, fallback="user")
    safe_exam_round_name = _safe_path_component(exam_round_name, fallback="exam")
    base_name = f"{safe_username}_{safe_exam_round_name}_{date_str}_오답재도전"

    retry_submission_dir = source_submission_dir.parent / base_name
    for i in count(1):
        if not retry_submission_dir.exists():
            break
        retry_submission_dir = source_submission_dir.parent / f"{base_name}_{i}"

    retry_submission_dir.mkdir(parents=True, exist_ok=False)

    retry_meta = {
        "exam_round_name": f"{exam_round_name} (오답만)",
        "username": username,
        "date": date_str,
        "pdf_path": meta.get("pdf_path"),
        "sb2_files": [str(path) for path in wrong_sb2],
        "answer_folder": meta.get("answer_folder"),
        "submission_dir": str(retry_submission_dir),
        "source_meta_path": str(meta_path),
        "source_submission_dir": str(source_submission_dir),
        "retry_mode": "wrong_only",
        "wrong_problem_keys": diagnostics["wrong_keys"],
        "pdf_page_indices": diagnostics["matched_original_indices"],
    }

    retry_meta_path = retry_submission_dir / "meta.json"
    with open(retry_meta_path, "w", encoding="utf-8") as f:
        json.dump(retry_meta, f, indent=4, ensure_ascii=False)

    return retry_meta_path, retry_submission_dir, retry_meta

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
        try:
            self.tk.call('tk', 'scaling', 1.25)   # 환경에 맞게 1.0~1.5
        except Exception:
            pass
        self.base_path = base_path
        print(f"ExamSelector self.base_path: {self.base_path}")

        # ✅ 추가: 공유 드롭박스(메인PC) 기본 경로 및 설정 로드

        self.share_dir = report_inbox         # ✅ 문제신고 전송 경로
        # ✅ 추가: 전역 config 참조 & 저장함수 자리(없으면 None)
        self.config = config
        self._save_config_func = None

        # ✅ 마지막 응시 meta.json 위치 기억 (시험 재개용)
        self.submission_meta_path = self.config.get("last_submission_meta_path")

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

        types_ = self.get_exam_types()
        if len(types_) == 1:
            only = types_[0]
            self.exam_type_var.set(only)
            self.update_exam_rounds()

        tk.Label(
            self, text="시험 회차를 선택하세요", font=("맑은 고딕", 13, "bold")
        ).pack(pady=10)

                # ✅ 시험 회차 콤보박스를 크게 보이도록 스타일 지정
        style = ttk.Style(self)
        style.configure(
            "Big.TCombobox",
            font=("맑은 고딕", 14),      # 드롭다운/입력창 글꼴 키우기
            padding=(8, 6, 24, 6),       # 좌/상/우/하 여백
        )

        # ✅ 드롭다운 리스트(각 회차 줄)의 글꼴도 같이 키우기
        self.option_add("*TCombobox*Listbox.font", ("맑은 고딕", 14))

        # style.configure(
        #     "Custom.TCombobox", font=("맑은 고딕", 13), padding=5  # 입력창 폰트
        # )
        self.exam_round_combo = ttk.Combobox(
            self,
            textvariable=self.exam_round_var,
            state="disabled",
            style="Big.TCombobox",      # ✅ 위에서 만든 스타일 사용
            width=28,                   # 살짝 줄여도 여백 때문에 더 커 보임
        )
        self.exam_round_combo["height"] = 8   # ✅ 한 번에 보이는 줄 수 (필요시 조절)
        self.exam_round_combo.pack(pady=8)

        btn_style = {
            "bg": "#007BFF",  # 파란색
            "fg": "white",  # 흰 글씨
            "font": ("맑은 고딕", 11, "bold"),  # ✅ 폰트 크기 ↑
            "activebackground": "#0056b3",
            "activeforeground": "white",
            "disabledforeground": "#999999",  # 비활성 상태에서 글자색
            "width": 20,
        }

        # self.start_btn = tk.Button(
        #     self,
        #     text="시험 시작",
        #     state="disabled",
        #     command=self.confirm_start,
        #     **btn_style,
        #     cursor="hand2",  # 👈 마우스 오버 시 손모양
        # )
        # self.start_btn.pack(pady=20)

        # regrade_btn_style = btn_style.copy()
        # regrade_btn_style["bg"] = "#28a745"  # 녹색
        # regrade_btn_style["activebackground"] = "#1e7e34"

        # self.regrade_btn = tk.Button(
        #     self,
        #     text="재채점 실행",
        #     command=self.select_folder_for_regrade,
        #     **regrade_btn_style,
        # )
        # self.regrade_btn.pack(pady=10)

        self.start_btn = tk.Button(
            self,
            text="시험 시작",
            state="disabled",
            command=self.confirm_start,
            **btn_style,
            cursor="hand2",  # 👈 마우스 오버 시 손모양
        )
        self.start_btn.pack(pady=20)

        # ✅ 시험 재개 버튼 (기존 meta.json 기준으로 이어하기)
        resume_btn_style = btn_style.copy()
        resume_btn_style["bg"] = "#6c757d"
        resume_btn_style["activebackground"] = "#5a6268"

        self.resume_btn = tk.Button(
            self,
            text="시험 재개하기",
            command=self.resume_exam_dialog,
            **resume_btn_style,
        )
        self.resume_btn.pack(pady=5)

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

        # ✅ 틀린 문제만 다시 풀기 버튼
        wrong_btn_style = btn_style.copy()
        wrong_btn_style["bg"] = "#ffc107"
        wrong_btn_style["fg"] = "black"
        wrong_btn_style["activebackground"] = "#e0a800"

        self.retry_wrong_btn = tk.Button(
            self,
            text="틀린 문제만 다시 풀기",
            command=self.retry_wrong_only_dialog,
            **wrong_btn_style,
        )
        self.retry_wrong_btn.pack(pady=5)

        self.bind("<Return>", lambda e: self._try_start())
        self.bind_all("<Alt-Left>", lambda e: self.show_exam_types())
        self._starting = False
        # self.label = tk.Label(self, text="시험 등급을 선택하세요", font=("Arial", 16))
        # self.label.pack(pady=20)

        # self.button_frame = tk.Frame(self)
        # self.button_frame.pack()

        # self.show_exam_types()

        # def set_icon(self):

    def confirm_start(self):
        if self._starting: return
        self._starting = True
        try:
            exam_type = self.exam_type_var.get()
            exam_round = self.exam_round_var.get()
            if exam_type and exam_round:
                selected_path = os.path.join(self.base_path, exam_type, exam_round)
                self.start_exam(selected_path)
        finally:
            self._starting = False

    # 클래스 메서드 추가
    def _try_start(self):
        if self.start_btn["state"] == "normal":
            self.confirm_start()
            
    def ask_username(self, initial=""):
        dlg = UsernameDialog(self, title="이름 입력", message="수험자 이름을 입력하세요:", initial=initial)
        self.wait_window(dlg)              # ← 다이얼로그 닫힐 때까지 블록
        return dlg.value


    def resume_exam_dialog(self):
        """기존 meta.json을 기준으로 시험을 다시 여는 기능 (시험 재개하기)"""
        from tkinter import filedialog

        meta_path = None

        # 1) config에 저장된 마지막 시험 meta.json이 있으면 먼저 물어보기
        last_meta = self.submission_meta_path or self.config.get("last_submission_meta_path")
        if last_meta and Path(last_meta).exists():
            if messagebox.askyesno(
                "시험 재개",
                f"마지막 응시 기록을 다시 여시겠습니까?\n\n{last_meta}",
                parent=self,
            ):
                meta_path = Path(last_meta)

        # 2) 위에서 사용하지 않으면 직접 meta.json 선택
        if meta_path is None:
            pick = filedialog.askopenfilename(
                title="재개할 시험의 meta.json 선택",
                filetypes=[("JSON 파일", "*.json")],
            )
            if not pick:
                return
            meta_path = Path(pick)

        # 3) meta.json 로드
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
        except Exception as e:
            messagebox.showerror("오류", f"meta.json 읽기 실패: {e}", parent=self)
            return

        pdf_path = meta.get("pdf_path")
        sb2_files = meta.get("sb2_files") or []
        submission_dir = Path(meta.get("submission_dir") or meta_path.parent)
        exam_round_name = meta.get("exam_round_name", "미지정")
        username = meta.get("username", "미입력")

        if not pdf_path or not sb2_files:
            messagebox.showerror("오류", "meta.json에 pdf_path / sb2_files 정보가 부족합니다.", parent=self)
            return
        if not submission_dir.exists():
            messagebox.showerror("오류", f"제출 폴더가 존재하지 않습니다:\n{submission_dir}", parent=self)
            return

        state_path = submission_dir / "exam_state.json"
        if not state_path.exists():
            messagebox.showerror(
                "시험 재개",
                "저장된 진행 상태(exam_state.json)가 없어 시험을 재개할 수 없습니다.",
                parent=self,
            )
            return

        # ✅ meta.json 안에 total_time이 있으면 이미 종료된 시험으로 판단
        if "total_time" in meta:
            messagebox.showinfo(
                "시험 재개",
                "이미 종료된 시험은 재개할 수 없습니다. 필요하면 재채점 기능을 사용하세요.",
                parent=self,
            )
            return

        problem_folder = os.path.dirname(sb2_files[0])

        # meta 경로 저장
        self.submission_meta_path = str(meta_path)
        self.config["last_submission_meta_path"] = self.submission_meta_path
        self._save_config()

        if not messagebox.askokcancel(
            "시험 재개",
            f"{username} 님의 '{exam_round_name}' 시험을 재개합니다.\n\n제출 폴더:\n{submission_dir}",
            parent=self,
        ):
            return

        # ✅ 기존 제출 폴더를 그대로 사용해서 ExamApp 실행
        self.destroy()
        app = ExamApp(
            pdf_path,
            sb2_files,
            problem_folder,
            submission_dir=submission_dir,
            exam_round_name=exam_round_name,
            username=username,
            pdf_page_indices=meta.get("pdf_page_indices"),
        )
        app.mainloop()

    def retry_wrong_only_dialog(self):
        """
        기존 제출 폴더에서 '틀린 문제만' 다시 푸는 모드
        - 제출폴더를 고르면 meta.json을 기준으로 채점 → 오답만 모아서 ExamApp 실행
        """
        from tkinter import filedialog
        from pathlib import Path

        folder = filedialog.askdirectory(title="틀린 문제만 다시 풀 제출 폴더 선택")
        if not folder:
            return
        folder = Path(folder)

        meta_path = folder / "meta.json"
        if not meta_path.exists():
            messagebox.showerror("오류", "선택한 폴더에 meta.json이 없습니다.", parent=self)
            return

        # 1) 오답 문제 목록 계산
        try:
            meta, wrong_sb2, diagnostics = _extract_retry_candidates(meta_path)
        except Exception as e:
            tb = traceback.format_exc()
            messagebox.showerror("오류", f"채점 중 오류 발생: {e}\n{tb}", parent=self)
            return

        # 2) 오답이 없으면 바로 종료
        if not diagnostics["wrong_keys"]:
            messagebox.showinfo("안내", "틀린 문제가 없습니다. 전부 정답입니다.", parent=self)
            return

        # 3) 오답 문제와 원본 문제 파일의 매핑 이상을 먼저 차단
        if diagnostics["duplicate_problem_keys"]:
            joined = "\n".join(diagnostics["duplicate_problem_keys"][:10])
            messagebox.showerror(
                "오류",
                "문제 파일 이름이 중복되어 오답 문제를 안정적으로 찾을 수 없습니다.\n"
                f"{joined}",
                parent=self,
            )
            return

        if diagnostics["unmatched_keys"]:
            joined = "\n".join(diagnostics["unmatched_keys"][:10])
            messagebox.showerror(
                "오류",
                "오답과 문제 파일을 매칭하지 못했습니다.\n"
                "파일 이름 규칙이 바뀌었는지 확인해주세요.\n\n"
                f"{joined}",
                parent=self,
            )
            return

        # 4) 오답 재도전용 새 세션 생성
        try:
            retry_meta_path, retry_submission_dir, retry_meta = _create_wrong_retry_session(
                meta_path,
                meta,
                wrong_sb2,
                diagnostics,
            )
        except Exception as e:
            tb = traceback.format_exc()
            messagebox.showerror("오류", f"오답 재도전 세션 생성 중 오류 발생: {e}\n{tb}", parent=self)
            return

        pdf_path = retry_meta.get("pdf_path")
        exam_round_name = retry_meta.get("exam_round_name", "미지정")
        username = retry_meta.get("username", "미입력")
        problem_folder = os.path.dirname(wrong_sb2[0])

        # 마지막 확인
        if not messagebox.askokcancel(
            "틀린 것만 다시 풀기",
            f"{username} 님의 '{exam_round_name}' 시험에서\n"
            f"{len(wrong_sb2)}개 문항만 다시 풉니다.\n\n"
            f"새 제출 폴더:\n{retry_submission_dir}",
            parent=self,
        ):
            try:
                shutil.rmtree(retry_submission_dir)
            except Exception:
                pass
            return

        # 5) 오답에 해당하는 문제들만 sb2 리스트로 넘겨서 ExamApp 실행
        self.submission_meta_path = str(retry_meta_path)
        self.config["last_submission_meta_path"] = self.submission_meta_path
        self._save_config()

        self.destroy()
        app = ExamApp(
            pdf_path,
            wrong_sb2,
            problem_folder,
            submission_dir=retry_submission_dir,
            exam_round_name=exam_round_name,
            username=username,
            load_state=False,  # ✅ 오답 전용 모드는 이전 exam_state.json을 무시
            pdf_page_indices=retry_meta.get("pdf_page_indices"),

        )
        app.mainloop()




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
        rounds = [folder for folder in os.listdir(exam_type_path)
                if os.path.isdir(os.path.join(exam_type_path, folder))]

        self.exam_round_combo["values"] = rounds
        self.exam_round_combo["state"] = "readonly"

        if len(rounds) == 1:
            self.exam_round_combo.set(rounds[0])
            self.start_btn["state"] = "normal"
        else:
            self.exam_round_combo.set("")
            self.start_btn["state"] = "disabled"

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
        # self.withdraw()
        username = self.ask_username(initial=self.config.get("last_username", ""))
        # self.deiconify()

        if not username:
            username = "미입력"
        else:
            # 다음 실행 때 기본값으로 보여주기
            self.config["last_username"] = username
            self._save_config()

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
                "다음 항목이 누락되었습니다: {}\n\n검사한 경로:\n{}".format(
                    ", ".join(missing), selected_path
                ),
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

        # ✅ 방금 생성한 meta.json 경로를 기억해 두었다가 '시험 재개하기'에서 사용
        self.submission_meta_path = str(meta_path)
        self.config["last_submission_meta_path"] = self.submission_meta_path
        self._save_config()


# ---- 클래스 바깥 전역에 정의된 함수들을 ExamSelector 메서드로 바인딩 ----
ExamSelector._open_settings_menu   = _open_settings_menu
ExamSelector._pick_exam_base_path  = _pick_exam_base_path
ExamSelector._pick_share_dir       = _pick_share_dir
ExamSelector._unique_prefix        = _unique_prefix
ExamSelector._send_issue_bundle    = _send_issue_bundle
ExamSelector._report_issue_dialog  = _report_issue_dialog
ExamSelector._save_config          = _save_config



class UsernameDialog(tk.Toplevel):
    def __init__(self, parent, title="이름 입력", message="수험자 이름을 입력하세요:", initial=""):
        super().__init__(parent)

        # try:
        #     # 윈도우 DPI 125~150%에서 글씨 작으면 1.25~1.5로 조정
        #     self.tk.call('tk', 'scaling', 1.25)
        # except Exception:
        #     pass

        # self.minsize(480, 620)  # 창 최소 크기 보장
        # self.resizable(False, False)  # 선택: 리사이즈 막기

        self.transient(parent)
        self.title(title)
        self.resizable(False, False)
        self.grab_set()
        self.value = None
        self.protocol("WM_DELETE_WINDOW", self.on_cancel)


        # 폰트 크게
        self.f_label = tkfont.Font(family="맑은 고딕", size=16, weight="bold")
        self.f_entry = tkfont.Font(family="맑은 고딕", size=16)
        self.f_btn   = tkfont.Font(family="맑은 고딕", size=14, weight="bold")

        pad = 16
        frm = tk.Frame(self, padx=pad, pady=pad)
        frm.pack(fill="both", expand=True)

        lbl = tk.Label(frm, text=message, font=self.f_label)
        lbl.pack(anchor="w", pady=(0, 8))

        self.entry = tk.Entry(frm, font=self.f_entry, width=24)
        self.entry.pack(fill="x", pady=(0, 12))
        if initial:
            self.entry.insert(0, initial)
        self.entry.select_range(0, tk.END)
        self.entry.focus_set()

        btns = tk.Frame(frm)
        btns.pack(fill="x")

        ok = tk.Button(
            btns, text="확인", font=self.f_btn, command=self.on_ok,
            bg="#007BFF", fg="white", activebackground="#0056b3", activeforeground="white"
        )
        ok.pack(side="right", padx=(8, 0))

        cancel = tk.Button(btns, text="취소", font=self.f_btn, command=self.on_cancel)
        cancel.pack(side="right")

        # 단축키
        self.bind("<Return>", lambda e: self.on_ok())
        self.bind("<Escape>", lambda e: self.on_cancel())

        # 가시성/포커스 확보
        self.update_idletasks()
        self.lift()
        self.attributes("-topmost", True)
        self.after(200, lambda: self.attributes("-topmost", False))

        # 중앙 배치
        self.after(10, lambda: self._center(parent, width=520, height=180))

    def _center(self, parent, width=520, height=180):
        self.update_idletasks()
        w = max(width, self.winfo_width())
        h = max(height, self.winfo_height())
        try:
            # 부모 중앙
            px, py = parent.winfo_rootx(), parent.winfo_rooty()
            pw, ph = parent.winfo_width(), parent.winfo_height()
            x = px + (pw - w) // 2
            y = py + (ph - h) // 2
        except Exception:
            # 폴백: 화면 중앙
            sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
            x = (sw - w) // 2
            y = (sh - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    def on_ok(self):
        val = self.entry.get().strip()
        if not val:
            messagebox.showwarning("입력 필요", "이름을 입력해주세요.", parent=self)
            return
        self.value = val
        self.destroy()

    def on_cancel(self):
        self.value = None
        self.destroy()
