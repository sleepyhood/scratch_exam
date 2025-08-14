import json
import os
from pathlib import Path
import zipfile
import filecmp
import re
import pprint
import html

from scratch_parser import interpret_block
import traceback

import re
from urllib.parse import quote
from pathlib import Path

def parse_paths(paths):
    parsed = []
    for path in paths:
        matches = re.findall(r"\[(\d+|'.+?'|\".+?\")\]", path)
        parsed_path = []
        for m in matches:
            if m.isdigit():
                parsed_path.append(int(m))
            else:
                parsed_path.append(m.strip("\"'"))
        parsed.append(parsed_path)
    return parsed


def blocks_are_equivalent(b1, b2):
    # 예: changeVar:by: vs setVar:to: + readVariable
    if b1[0] == "changeVar:by:" and b2[0] == "setVar:to:":
        var1, delta = b1[1], b1[2]
        var2, expr = b2[1], b2[2]

        if var1 != var2:
            return False
        # b2가 ["+", ["readVariable", var], delta]인지 확인
        if isinstance(expr, list) and expr[0] == "+":
            if expr[1] == ["readVariable", var2] and expr[2] == delta:
                return True
        return False

    return b1 == b2  # 기본적으로는 구조 비교


def scripts_are_equivalent(scripts1, scripts2):
    if len(scripts1) != len(scripts2):
        return False

    for blocks1, blocks2 in zip(scripts1, scripts2):
        if len(blocks1) != len(blocks2):
            return False

        for b1, b2 in zip(blocks1, blocks2):
            if not blocks_are_equivalent(b1, b2):
                return False
    return True


# 병렬로 작동하는 코드의 순서를 비교하는 에러가 생겼음
def clean_scripts(scripts):
    def clean_block(block):
        if isinstance(block, list):
            return [clean_block(b) for b in block if b is not None]
        return block if block is not None else "__EMPTY__"

    if not scripts:
        return []

    # 좌표 제거 후, 블록 순서를 문자열 기준으로 정렬
    cleaned = [clean_block(blocks) for _, _, blocks in scripts]
    cleaned_sorted = sorted(cleaned, key=lambda b: str(b))
    return cleaned_sorted


IGNORE_COSTUME_IMAGE = True  # True면 baseLayerMD5 무시, False면 정확히 비교


def costumes_are_equivalent(c1, c2):
    if len(c1) != len(c2):
        return False

    for cos1, cos2 in zip(c1, c2):
        if cos1.get("costumeName") != cos2.get("costumeName"):
            return False

        if not IGNORE_COSTUME_IMAGE:
            if cos1.get("baseLayerMD5") != cos2.get("baseLayerMD5"):
                return False

    return True


# def find_first_diff_element(a, b, path=""):
#     """
#     재귀적으로 두 리스트(또는 값)를 비교해 첫 번째 다른 위치를 찾아서
#     차이 위치를 문자열로 반환.
#     path: 위치 추적용 (예: '[2][1]')
#     """
#     if type(a) != type(b):
#         return path or "root"

#     if isinstance(a, list):
#         min_len = min(len(a), len(b))
#         for i in range(min_len):
#             sub_path = f"{path}[{i}]"
#             diff = find_first_diff_element(a[i], b[i], sub_path)
#             if diff:
#                 return diff
#         if len(a) != len(b):
#             return f"{path}[length differs]"
#         return None
#     else:
#         if a != b:
#             return path or "root"
#         return None


# 모든 에러 보여주기
def find_all_diff_elements(a, b, path=""):
    """
    두 값이나 리스트를 비교해 모든 차이 위치를 리스트로 반환.
    """
    diffs = []

    if type(a) != type(b):
        diffs.append(path or "root")
        return diffs

    if isinstance(a, list):
        min_len = min(len(a), len(b))
        for i in range(min_len):
            sub_path = f"{path}[{i}]"
            diffs += find_all_diff_elements(a[i], b[i], sub_path)
        if len(a) != len(b):
            diffs.append(f"{path}[length differs]")
    else:
        if a != b:
            diffs.append(path or "root")

    return diffs

def make_diff_html(expected_scripts, actual_scripts, sprite_name=""):
    diff_rows = []
    for script_idx, (exp_blocks, act_blocks) in enumerate(
        zip(expected_scripts, actual_scripts)
    ):
        for block_idx, (b_exp, b_act) in enumerate(zip(exp_blocks, act_blocks)):
            if not blocks_are_equivalent(b_exp, b_act):
                diff_positions = find_all_diff_elements(b_exp, b_act)
                parsed_paths = parse_paths(diff_positions)

                # ✅ exp = 정답, act = 제출
                exp_str = interpret_block(b_exp, highlight_paths=parsed_paths)
                act_str = interpret_block(b_act, highlight_paths=parsed_paths)

                block_html = f"""
<br/><p><strong>🎯 '{sprite_name}' 스크립트 {script_idx + 1}번 블록 {block_idx} 오류</strong></p>
<p>차이 위치: <code>{", ".join(diff_positions)}</code></p>
<table class="diff-table">
  <thead>
    <tr><th>✅ 정답</th><th>❌ 제출</th></tr>
  </thead>
  <tbody>
    <tr>
      <td><div class='block-display correct'>{exp_str}</div></td>
      <td><div class='block-display wrong'>{act_str}</div></td>
    </tr>
  </tbody>
</table>
"""
                diff_rows.append(block_html)

    return "<hr>".join(diff_rows)


# def make_diff_html(expected_scripts, actual_scripts, sprite_name=""):
#     diff_messages = []
#     print(f"expected_scripts: {expected_scripts}\n\n\n\n")
#     print(f"actual_scripts: {actual_scripts}\n\n\n")
#     for script_idx, (exp_blocks, act_blocks) in enumerate(
#         zip(expected_scripts, actual_scripts)
#     ):
#         for block_idx, (b_exp, b_act) in enumerate(zip(exp_blocks, act_blocks)):
#             print(f"block_idx: {block_idx}")
#             if not blocks_are_equivalent(b_exp, b_act):
#                 diff_positions = find_all_diff_elements(b_exp, b_act)
#                 diff_pos_str = ", ".join(diff_positions)

#                 # exp_str = html.escape(interpret_block(b_exp))
#                 # act_str = html.escape(interpret_block(b_act))

#                 # 색상이 바꿀거면 이스케이프 안하기
#                 # 근데 매줄마다 스타일 바꿔줘야함...
#                 # exp_str = interpret_block(b_exp)
#                 # act_str = interpret_block(b_act)

#                 # exp_str = interpret_block(b_exp, highlight_paths=diff_positions)
#                 # act_str = interpret_block(b_act, highlight_paths=diff_positions)
#                 exp_str = interpret_block(
#                     b_exp, highlight_paths=parse_paths(diff_positions)
#                 )
#                 act_str = interpret_block(
#                     b_act, highlight_paths=parse_paths(diff_positions)
#                 )
#                 print(f"diff_positions: {diff_positions}")
#                 # print(f"act_str: {act_str}")

#                 diff_msg = (
#                     f"<div style='margin-bottom: 1em;'>"
#                     f"<br/><strong>🎯 '{sprite_name}' 스프라이트 스크립트 {script_idx + 1}번 블록 {block_idx} 오류</strong><br>"
#                     f"차이 위치: <code>{diff_pos_str}</code><br><br>"
#                     f"<strong>✅ 정답:</strong><br>"
#                     f"<div class='block-display correct'>{act_str}</div><br/>"
#                     f"<strong>❌ 제출:</strong><br>"
#                     f"<div class='block-display wrong'>{exp_str}</div>"
#                     f"</div>"
#                 )
#                 diff_messages.append(diff_msg)

#     return "<hr>".join(diff_messages) if diff_messages else ""


def compare_normalized_projects(s_project, a_project):
    errors = []
    diff_count = 0  # 차이난 블록 수 카운트

    # 1) ✅ 배경(Stage) 먼저 비교
    s_stage = s_project.get("stage", {})
    a_stage = a_project.get("stage", {})

    # 빈 블록 검사
    if "__EMPTY__" in str(s_stage.get("scripts")):
        errors.append("'배경'에 비어 있는 블록 있음")
    else:
        # 스크립트 비교
        if not scripts_are_equivalent(s_stage.get("scripts", []), a_stage.get("scripts", [])):
            diff_html = make_diff_html(
                a_stage.get("scripts", []),   # ✅ 정답 먼저
                s_stage.get("scripts", []),   # ❌ 제출 나중
                sprite_name="배경"
            )
            errors.append(diff_html)
            diff_count += 1

    # 코스튬 비교
    if not costumes_are_equivalent(s_stage.get("costumes", []), a_stage.get("costumes", [])):
        errors.append("'배경'의 모양 다름")

    # 사운드 비교
    if s_stage.get("sounds") != a_stage.get("sounds"):
        errors.append("'배경'의 소리 다름")

    # 2) ✅ 스프라이트 비교 (기존 로직 보강)
    s_sprites = {s["objName"]: s for s in s_project["sprites"]}
    a_sprites = {s["objName"]: s for s in a_project["sprites"]}

    all_names = set(s_sprites.keys()).union(a_sprites.keys())

    for name in sorted(all_names):
        # "보기블럭"은 채점에서 제외
        if name.replace(" ", "") in [
            "보기블럭",
            "보기블록",
            "보기블록1",
            "보기블록2",
            "보기블록3",
            "보기블록4",
        ]:
            continue

        s = s_sprites.get(name)
        a = a_sprites.get(name)

        print(s.get("costumes", []))  # 비교 대상 costume 출력해보기
        print(a.get("costumes", []))  # 비교 대상 costume 출력해보기

        if s is None:
            errors.append(f"스프라이트 '{name}'가 제출본에 없음")
            continue
        if a is None:
            errors.append(f"스프라이트 '{name}'가 정답에 없음")
            continue

        if "__EMPTY__" in str(s.get("scripts")):
            errors.append(f"'{name}' 스프라이트에 비어 있는 블록 있음")
            continue

        # scripts 비교
        # if s.get("scripts") != a.get("scripts"):
        #     errors.append(f"'{name}' 스프라이트의 스크립트 다름")

        # 스크립트 비교
        if not scripts_are_equivalent(s.get("scripts", []), a.get("scripts", [])):
            diff_html = make_diff_html(
                a.get("scripts", []),  # ✅ 정답 먼저
                s.get("scripts", []),  # ❌ 제출 나중
                sprite_name=name
            )
            errors.append(diff_html)
            diff_count += 1


        # costumes 비교
        # if s.get("costumes") != a.get("costumes"):
        if not costumes_are_equivalent(s.get("costumes", []), a.get("costumes", [])):

            errors.append(f"'{name}' 스프라이트의 모양 다름")

        # sounds 비교
        if s.get("sounds") != a.get("sounds"):
            errors.append(f"'{name}' 스프라이트의 소리 다름")

    if diff_count > 0:
        errors.append(f"<strong>총 {diff_count}개 블록에서 차이 발견됨</strong>")

    return errors


def extract_json_from_sb2(sb2_path):
    print(f"{sb2_path}의 json 출력: ")
    with zipfile.ZipFile(sb2_path, "r") as zf:
        with zf.open("project.json") as f:
            # data = json.load(f)  # dict로 로딩
            # print(data)  # {'key': 'value'}
            return json.load(f)


def normalize_project_json(project_json, ignore_costume_image=True):
    def clean_scripts(scripts):
        def clean_block(block):
            if isinstance(block, list):
                return [clean_block(b) for b in block if b is not None]
            return block if block is not None else "__EMPTY__"

        if not scripts:
            return []

        # 좌표 제거 + 블록 내용만 추출
        cleaned = [clean_block(blocks) for _, _, blocks in scripts]
        # 순서 무시를 위해 정렬
        return sorted(cleaned, key=lambda x: str(x))

    def extract_essential_sprite(sprite):
        return {
            "objName": sprite.get("objName"),
            "scripts": clean_scripts(sprite.get("scripts")),
            "costumes": sorted(
                [
                    {
                        "costumeName": c.get("costumeName", "") or "",
                        **(
                            {}
                            if ignore_costume_image
                            else {"baseLayerMD5": c.get("baseLayerMD5", "") or ""}
                        ),
                    }
                    for c in sprite.get("costumes", [])
                    if c.get("costumeName")
                    and (ignore_costume_image or c.get("baseLayerMD5"))
                ],
                key=lambda x: x.get("costumeName") or "",
            ),
            "sounds": sorted(
                [
                    {"soundName": s.get("soundName", ""), "md5": s.get("md5", "")}
                    for s in sprite.get("sounds", [])
                    if s.get("soundName") and s.get("md5")
                ],
                key=lambda x: x.get("soundName") or "",
            ),
        }

    children = project_json.get("children", [])
    normalized_children = sorted(
        [
            extract_essential_sprite(sprite)
            for sprite in children
            if isinstance(sprite, dict) and sprite.get("objName") is not None
        ],
        key=lambda s: s.get("objName") or "",
    )

    return {
        "stage": {
            "costumes": sorted(
                [
                    {
                        "costumeName": c.get("costumeName", "") or "",
                        **(
                            {}
                            if ignore_costume_image
                            else {"baseLayerMD5": c.get("baseLayerMD5", "") or ""}
                        ),
                    }
                    for c in project_json.get("costumes", [])
                    if c.get("costumeName")
                    and (ignore_costume_image or c.get("baseLayerMD5"))
                ],
                key=lambda x: x.get("costumeName") or "",
            ),
            "sounds": sorted(
                [
                    {"soundName": s.get("soundName", ""), "md5": s.get("md5", "")}
                    for s in project_json.get("sounds", [])
                    if s.get("soundName") and s.get("md5")
                ],
                key=lambda x: x.get("soundName") or "",
            ),

                    # ✅ 배경(Stage) 스크립트 포함
        "scripts": clean_scripts(project_json.get("scripts")),
        },
        "sprites": normalized_children,
    }


def normalize_name(name: str):
    # COS3_01_05_기출유형파악하기03-연습01 문제_제출 → cos30105기출유형파악하기03연습01
    for token in ["문제", "정답", "제출", "_", " "]:
        name = name.replace(token, "")
    return name.lower()


def grade_from_meta(meta_path):
    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)

    submission_dir = Path(meta["submission_dir"])
    answer_dir = Path(meta["answer_folder"])

    results = []

    for i, submit_file in enumerate(submission_dir.glob("*_제출.sb2")):
        base = normalize_name(submit_file.stem)

        # PDF 찾기
        # raw_path = meta.get("pdf_path")
        raw_path_list = list(submission_dir.glob("*.pdf"))
        pdf_full_path = None

        if raw_path_list:
            # 첫 번째 PDF 선택
            first_pdf_path = raw_path_list[0].resolve()  # Path 객체
            cleaned = str(first_pdf_path).replace("\\", "/")  # 문자열로 바꾼 후 슬래시 정리
            pdf_full_path = "file:///" + cleaned  # 세 개 슬래시 주의!
            print(f"pdf_full_path: {pdf_full_path}")
        # print(f"pdf_rel_path//pdf_rel_path}")
        # 정답 후보 찾기
        matched_answer = None
        for ans_file in answer_dir.glob("*.sb2"):
            ans_base = normalize_name(ans_file.stem)
            if ans_base == base:
                matched_answer = ans_file
                break

        if not matched_answer:
            results.append(
                {
                    "제출": submit_file.name,
                    "제출파일경로": str(submit_file),  # ✅ 여기 추가
                    "정답": None,
                    "정답여부": "❌ 정답 없음",
                }
            )
            continue

        try:
            s_json = extract_json_from_sb2(submit_file)
            print(f"s_json: {s_json}")
            a_json = extract_json_from_sb2(matched_answer)
            print(f"a_json: {a_json}")

        except Exception as e:
            results.append({"오류내용": f"[project.json 추출 실패] {e}"})
            continue

        try:
            s_normalized = normalize_project_json(s_json)
            print(f"s_normalized: {s_normalized}")
            a_normalized = normalize_project_json(a_json)
            print(f"a_normalized: {a_normalized}")

        except Exception as e:
            print("▶ 정규화 중 예외 발생! 🔥")
            print("s_json keys:", s_json.keys())
            print("a_json keys:", a_json.keys())
            results.append({"오류내용": f"[정규화 실패] {e}"})
            continue

        try:
            # pp = pprint.PrettyPrinter(indent=2, width=120, compact=False)
            # pp.pprint(s_normalized)

            # pp.pprint(a_normalized)

            # 100점일 경우
            if s_normalized == a_normalized:
                results.append(
                    {
                        "제출": submit_file.name,
                        "제출파일경로": str(submit_file),  # ✅ 여기 추가
                        "정답": matched_answer.name,
                        "정답여부": "O",
                        "문제PDF": pdf_full_path ,  # 🔍 추가된 항목
                            "시작페이지": i + 1,  # ← 1번부터 시작하도록 인덱스 + 1

                    }
                )
            else:
                # 차이점 수집
                diff_errors = compare_normalized_projects(s_normalized, a_normalized)
                print(f"diff_errors: {diff_errors}")
                tmp = str(s_normalized) + "\n\n" + str(a_normalized)
                results.append(
                    {
                        "제출": submit_file.name,
                        "제출파일경로": str(submit_file),  # ✅ 여기 추가
                        "정답": matched_answer.name,
                        "정답여부": "X",
                        "오류내용": "; ".join(diff_errors),
                        "문제PDF": pdf_full_path ,  # 🔍 추가된 항목
                            "시작페이지": i + 1,  # ← 1번부터 시작하도록 인덱스 + 1

                    }
                )
        except Exception as e:
            tb = traceback.format_exc()

            results.append(
                {
                    "제출": submit_file.name,
                    "제출파일경로": str(submit_file),  # ✅ 여기 추가
                    "정답": matched_answer.name,
                    "정답여부": "오류",
                    "오류내용": f"[normalize or compare 중 오류] {e}\n{tb}",
                    "문제PDF": pdf_full_path,  # 🔍 추가된 항목
                        "시작페이지": i + 1,  # ← 1번부터 시작하도록 인덱스 + 1

                }
            )

    return results


def print_results(results):
    correct = sum(1 for r in results if r["정답여부"] == "O")
    total = len(results)
    print(f"\n📝 채점 결과: {correct} / {total} 문제 정답\n")

    for r in results:
        status = r["정답여부"]
        line = f"[제출: {r['제출']}] → 정답여부: {status}"
        if r.get("정답"):
            line += f" | 정답: {r['정답']}"
        if status == "오류" or r.get("오류내용"):
            line += f"\n    ⚠ 오류내용: {r['오류내용']}"
        print(line)
    print("\n\n")


def regrade_submission_folder(folder_path):
    """
    제출 폴더에 있는 meta.json을 기준으로 재채점 실행
    """
    meta_path = Path(folder_path) / "meta.json"
    if not meta_path.exists():
        print(f"⚠ meta.json이 없습니다: {meta_path}")
        return

    results = grade_from_meta(meta_path)
    print_results(results)

    # html_report.py와 연동도 가능
    from html_report import save_results_as_html

    # save_results_as_html(results, meta_path, regrade_count=1)
    save_results_as_html(results, meta_path=meta_path, regrade_mode=True)
