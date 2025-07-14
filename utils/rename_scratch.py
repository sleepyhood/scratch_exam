import os
import shutil
import re
import tkinter as tk
from tkinter import filedialog, messagebox


def relabel_files_in_folder():
    folder_path = filedialog.askdirectory(title="문제/정답 폴더 선택")
    if not folder_path:
        return

    folder_name = os.path.basename(folder_path)
    if not ("문제" in folder_name or "정답" in folder_name):
        messagebox.showerror(
            "폴더 이름 오류", "'문제' 또는 '정답'이 포함된 폴더만 가능합니다."
        )
        return

    mode = "문제" if "문제" in folder_name else "정답"

    grade = grade_var.get().strip()
    chapter = chapter_var.get().strip().zfill(2)
    prefix = f"COS{grade}_{chapter}_"

    files = sorted(os.listdir(folder_path))
    renamed = 0

    for idx, fname in enumerate(files):
        if not fname.endswith(".sb2"):
            continue

        src_path = os.path.join(folder_path, fname)
        base = os.path.splitext(fname)[0]
        number = f"{idx+1:02d}"

        # 파일명이 번호뿐일 수도 있으므로 의미있는 텍스트 추출
        clean_title = re.sub(r"\s+", "", base)
        clean_title = (
            clean_title.replace("-", "")
            .replace("문제", "")
            .replace("정답", "")
            .replace("답", "")
        )
        clean_title = clean_title if clean_title else f"Q{number}"

        new_name = f"{prefix}{number}_{clean_title}_{mode}.sb2"
        dst_path = os.path.join(folder_path, new_name)

        os.rename(src_path, dst_path)
        renamed += 1

    messagebox.showinfo("리네이밍 완료", f"{renamed}개 파일에 접두사/접미사 적용 완료")


def relabel_answers_using_problem_titles():
    answer_folder = filedialog.askdirectory(title="정답 폴더 선택")
    if not answer_folder or not answer_folder.endswith("정답"):
        messagebox.showerror("오류", "'정답'으로 끝나는 폴더만 선택하세요.")
        return

    # 문제 폴더 유추
    problem_folder = answer_folder.replace("정답", "문제")
    if not os.path.exists(problem_folder):
        messagebox.showerror(
            "오류", f"해당 문제 폴더가 존재하지 않습니다:\n{problem_folder}"
        )
        return

    problem_files = sorted(
        [f for f in os.listdir(problem_folder) if f.endswith("_문제.sb2")]
    )
    answer_files = sorted([f for f in os.listdir(answer_folder) if f.endswith(".sb2")])

    if len(problem_files) != len(answer_files):
        if not messagebox.askyesno(
            "주의",
            f"문제({len(problem_files)}개)와 정답({len(answer_files)}개) 수가 다릅니다. 그래도 계속할까요?",
        ):
            return

    renamed = 0
    for p_fname, a_fname in zip(problem_files, answer_files):
        base_name = p_fname.replace("_문제.sb2", "")
        new_name = base_name + "_정답.sb2"
        old_path = os.path.join(answer_folder, a_fname)
        new_path = os.path.join(answer_folder, new_name)
        os.rename(old_path, new_path)
        renamed += 1

    messagebox.showinfo(
        "정답 리네이밍 완료",
        f"{renamed}개 정답 파일 이름이 문제 이름 기반으로 변경되었습니다.",
    )


def create_dummy_answers():
    problem_path = filedialog.askdirectory(title="문제 폴더 선택")
    if not problem_path:
        return

    if not problem_path.endswith("문제"):
        messagebox.showerror(
            "경고", "폴더명이 '문제'로 끝나는 폴더만 선택할 수 있습니다."
        )
        return

    answer_path = problem_path.replace("문제", "정답")
    if not os.path.exists(answer_path):
        os.makedirs(answer_path)

    created = 0
    for fname in os.listdir(problem_path):
        if not fname.endswith("_문제.sb2"):
            continue

        answer_name = fname.replace("_문제.sb2", "_정답.sb2")
        answer_file = os.path.join(answer_path, answer_name)

        if not os.path.exists(answer_file):
            shutil.copy(os.path.join(problem_path, fname), answer_file)
            created += 1

    # 정답 누락이 있어 생성된 경우 → 상위 폴더명에 (정답 미완성) 추가
    if created > 0:
        base_dir = os.path.dirname(problem_path)  # COS3_01_문제의 상위 폴더
        if not base_dir.endswith("(정답 미완성)"):
            new_base = base_dir + " (정답 미완성)"
            try:
                os.rename(base_dir, new_base)
                messagebox.showinfo(
                    "정답 생성 완료",
                    f"{created}개 정답 파일 생성\n\n📌 폴더명 수정됨:\n{os.path.basename(new_base)}",
                )
            except Exception as e:
                messagebox.showwarning(
                    "폴더 이름 수정 실패",
                    f"정답 파일은 생성되었지만 폴더명 변경 실패:\n{e}",
                )
        else:
            messagebox.showinfo(
                "정답 생성 완료",
                f"{created}개 정답 파일 생성\n(이미 폴더명에 '정답 미완성' 표시됨)",
            )
    else:
        messagebox.showinfo(
            "정답 생성 완료", "모든 문제에 대응되는 정답 파일이 이미 존재합니다."
        )


def rename_and_organize(folder_path, grade="3", chapter="01", folder_title="기출유형1"):
    prefix = f"COS{grade}_{chapter}_"

    parent_dir = os.path.dirname(folder_path)
    new_folder_name = f"{chapter}. {grade}급 {folder_title}"
    new_folder_path = os.path.join(parent_dir, new_folder_name)
    os.makedirs(new_folder_path, exist_ok=True)

    # 서브폴더 생성
    problem_folder = os.path.join(new_folder_path, f"{prefix}문제")
    answer_folder = os.path.join(new_folder_path, f"{prefix}정답")
    os.makedirs(problem_folder, exist_ok=True)
    os.makedirs(answer_folder, exist_ok=True)

    files = sorted(os.listdir(folder_path))
    index = 1

    for fname in files:
        if fname.endswith(".pdf"):
            new_pdf_name = f"{prefix}{folder_title}.pdf"
            shutil.copy(
                os.path.join(folder_path, fname),
                os.path.join(new_folder_path, new_pdf_name),
            )
        elif fname.endswith(".sb2"):
            base_name = os.path.splitext(fname)[0]
            is_answer = "정답" in base_name or "답" in base_name

            new_number = f"{index:02d}"
            clean_title = (
                re.sub(r"\s+", "", base_name)
                .replace("-", "")
                .replace("문제", "")
                .replace("정답", "")
            )
            new_name = f"{prefix}{new_number}_{clean_title}_{'정답' if is_answer else '문제'}.sb2"

            shutil.copy(
                os.path.join(folder_path, fname),
                os.path.join(answer_folder if is_answer else problem_folder, new_name),
            )
            index += 1

    messagebox.showinfo("완료", f"[완료] {folder_path} → {new_folder_path}")


# ------------------- GUI 구성 -------------------


def browse_folder():
    folder = filedialog.askdirectory()
    folder_var.set(folder)


def run_organize():
    folder_path = folder_var.get()
    grade = grade_var.get().strip()
    chapter = chapter_var.get().strip().zfill(2)
    title = title_var.get().strip()

    if not (folder_path and grade and chapter and title):
        messagebox.showwarning("입력 오류", "모든 입력란을 채워주세요.")
        return

    if not os.path.exists(folder_path):
        messagebox.showerror("경로 오류", "선택한 폴더 경로가 유효하지 않습니다.")
        return

    try:
        rename_and_organize(folder_path, grade, chapter, title)
    except Exception as e:
        messagebox.showerror("오류 발생", str(e))


# ------------------- GUI 초기화 -------------------

root = tk.Tk()
root.title("스크래치 파일 자동 리네이밍")

tk.Label(root, text="① 정리할 폴더 선택").grid(row=0, column=0, sticky="w")
folder_var = tk.StringVar()
tk.Entry(root, textvariable=folder_var, width=50).grid(
    row=1, column=0, columnspan=2, padx=5
)
tk.Button(root, text="폴더 선택", command=browse_folder).grid(row=1, column=2, padx=5)

tk.Label(root, text="② 등급 (예: 2, 3)").grid(row=2, column=0, sticky="w")
grade_var = tk.StringVar()
tk.Entry(root, textvariable=grade_var, width=10).grid(row=2, column=1, sticky="w")

tk.Label(root, text="③ 회차 번호 (예: 1, 2)").grid(row=3, column=0, sticky="w")
chapter_var = tk.StringVar()
tk.Entry(root, textvariable=chapter_var, width=10).grid(row=3, column=1, sticky="w")

tk.Label(root, text="④ 폴더 제목 (예: 기출유형1)").grid(row=4, column=0, sticky="w")
title_var = tk.StringVar()
tk.Entry(root, textvariable=title_var, width=30).grid(row=4, column=1, sticky="w")

tk.Button(
    root, text="✅ 실행 (리네이밍 시작)", command=run_organize, bg="lightgreen"
).grid(row=5, column=0, columnspan=3, pady=10)

tk.Button(
    root,
    text="📄 문제 기반 임시 정답 파일 만들기",
    command=create_dummy_answers,
    bg="skyblue",
).grid(row=6, column=0, columnspan=3, pady=5)

tk.Button(
    root, text="✏️ 접두사/접미사 리네이밍", command=relabel_files_in_folder, bg="orange"
).grid(row=7, column=0, columnspan=3, pady=5)

tk.Button(
    root,
    text="🧩 정답 → 문제명 기반 리네이밍",
    command=relabel_answers_using_problem_titles,
    bg="lightcoral",
).grid(row=8, column=0, columnspan=3, pady=5)

root.mainloop()
