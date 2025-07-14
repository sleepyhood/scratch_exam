import os
import json

# 기준 디렉토리
base_dir = r"#수업용_프로그램\scratch_exam\자격증 준비"

# 메타데이터 저장
metadata = {}

# .sb2 파일 재귀적으로 탐색
for root, dirs, files in os.walk(base_dir):
    for file in files:
        if not file.endswith(".sb2"):
            continue

        full_path = os.path.join(root, file)
        relative_path = os.path.relpath(full_path, base_dir)

        # 문제 ID 추출
        match = None
        if file.endswith("_ans.sb2"):
            match = file.replace("_ans.sb2", "")
            if match not in metadata:
                metadata[match] = {}
            metadata[match]["answer_path"] = relative_path
        else:
            match = file.replace(".sb2", "")
            if match not in metadata:
                metadata[match] = {}
            metadata[match]["problem_path"] = relative_path

# 저장
output_path = os.path.join(base_dir, "metadata.json")
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(metadata, f, indent=2, ensure_ascii=False)

print(f"✅ metadata.json 생성 완료: {output_path}")
