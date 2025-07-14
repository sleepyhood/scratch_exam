import os
import shutil

# 기준 루트 디렉터리
base_dir = r"#수업용_프로그램\scratch_exam\자격증 준비"

# 정답/문제 키워드 정의
problem_keywords = ["문제", "문제파일", "문제 파일"]
answer_keywords = ["정답", "정답파일", "정답 파일"]

def is_problem_folder(name):
    return any(k in name for k in problem_keywords)

def is_answer_folder(name):
    return any(k in name for k in answer_keywords)

def find_matching_folders(base_path):
    candidates = {}
    for root, dirs, files in os.walk(base_path):
        for d in dirs:
            full_path = os.path.join(root, d)
            parent = os.path.basename(os.path.dirname(full_path))

            if is_problem_folder(d) or is_answer_folder(d):
                key = parent
                if key not in candidates:
                    candidates[key] = {"problem": None, "answer": None}
                if is_problem_folder(d):
                    candidates[key]["problem"] = full_path
                elif is_answer_folder(d):
                    candidates[key]["answer"] = full_path
    return candidates

def reorganize_folders():
    pairs = find_matching_folders(base_dir)
    for parent_name, folders in pairs.items():
        problem_dir = folders["problem"]
        answer_dir = folders["answer"]

        if not problem_dir or not answer_dir:
            print(f"⚠️ 쌍이 완전하지 않음: {parent_name}")
            continue

        files = sorted(os.listdir(problem_dir))
        for i, filename in enumerate(files, 1):
            problem_path = os.path.join(problem_dir, filename)
            answer_path = os.path.join(answer_dir, filename)
            if not os.path.exists(problem_path) or not os.path.exists(answer_path):
                print(f"❌ 쌍이 누락됨: {filename}")
                continue

            new_id = f"P{i:03}"
            new_folder = os.path.join(os.path.dirname(problem_dir), new_id)
            os.makedirs(new_folder, exist_ok=True)

            shutil.copy(problem_path, os.path.join(new_folder, "문제.sb2"))
            shutil.copy(answer_path, os.path.join(new_folder, "정답.sb2"))

            print(f"✅ {filename} → {new_folder}")

if __name__ == "__main__":
    reorganize_folders()
