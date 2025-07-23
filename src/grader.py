import json
import os
from pathlib import Path
import zipfile
import filecmp
import re
import pprint


def interpret_block(block, depth=0):
    indent = "  " * depth

    if not isinstance(block, list):
        return str(block)

    opcode = block[0]

    # 인자 확인
    # 1번 인덱스 없이 제출된 경우도 존재할 수 있다. (반복문에 조건이 없다던지...)
    args = block[1:] if len(block) > 1 else []

    # 변수 설정
    if opcode == "setVar:to:":
        if len(block) >= 3:
            var_name = block[1]
            expr = interpret_block(block[2])
            return f"{var_name}를 {expr}으로 정하기"
        else:
            return "변수 설정 블록 (인자 부족)"

    # 변수 값 읽기
    elif opcode == "readVariable":
        var_name = block[1]
        if var_name == "answer":
            return "대답"
        if var_name == "timer":
            return "타이머"
        else:
            return var_name

    # 연산: 더하기
    elif opcode == "+":
        left = interpret_block(block[1])
        right = interpret_block(block[2])
        return f"({left} 더하기 {right})"

    # 연산: 빼기
    elif opcode == "-":
        left = interpret_block(block[1])
        right = interpret_block(block[2])
        return f"({left} 빼기 {right})"

    # 연산: 곱하기
    elif opcode == "*":
        left = interpret_block(block[1])
        right = interpret_block(block[2])
        return f"({left} 곱하기 {right})"

    # 연산: 나누기
    elif opcode == "/":
        left = interpret_block(block[1])
        right = interpret_block(block[2])
        return f"({left} 나누기 {right})"

    # 난수 생성 (min ~ max)
    elif opcode == "randomFrom:to:":
        min_val = interpret_block(block[1])
        max_val = interpret_block(block[2])
        return f"{min_val}부터 {max_val}까지 난수 생성"

    # 이동 (x, y) 방향으로 이동
    elif opcode == "move:steps:":
        steps = interpret_block(block[1])
        return f"{steps}만큼 이동하기"

    # 위치 설정
    elif opcode == "gotoX:y:":
        x = interpret_block(block[1])
        y = interpret_block(block[2])
        return f"x 좌표 {x}, y 좌표 {y}로 이동하기"

    # 방향 설정
    elif opcode == "pointInDirection:":
        direction = interpret_block(block[1])
        return f"방향을 {direction}도로 설정하기"

    # 변수 값 증가
    elif opcode == "changeVar:by:":
        var_name = block[1]
        delta = interpret_block(block[2])
        return f"{var_name}를 {delta}만큼 더하기"

    # 이벤트: 시작했을 때
    elif opcode == "whenGreenFlag":
        return "초록 깃발 클릭했을 때"

    # 이벤트: 스프라이트 클릭했을 때
    elif opcode == "whenClicked":
        return "스프라이트 클릭했을 때"

    # 제어: 반복 (횟수)
    elif opcode == "repeat:times:":
        times = interpret_block(block[1])
        return f"{times}번 반복하기"

    # 제어: 만약 ~ 이면
    elif opcode == "if:":
        condition = interpret_block(block[1])
        return f"{indent}만약 {condition}이면:\n\t" + "\n".join("  " + interpret_block(b, depth+1) for b in inner_blocks)

    # 제어: 만약 ~ 이고 아니면
    elif opcode == "if:else:":
        condition = interpret_block(block[1])
        return f"만약 {condition}이면, 아니면"

    # # 제어: 계속 반복하기 (무한반복)
    # elif opcode == "forever":
    #     return "계속 반복하기"

    # 제어: 기다리기 (초)
    elif opcode == "wait:elapsed:from:":
        seconds = interpret_block(block[1])
        return f"{seconds}초 기다리기"

    # 형태: 의상 바꾸기
    elif opcode == "switchCostumeTo:":
        costume = interpret_block(block[1])
        return f"의상을 {costume}(으)로 바꾸기"

    # 형태: 효과 적용하기
    elif opcode == "changeEffect:by:":
        effect = interpret_block(block[1])
        amount = interpret_block(block[2])
        return f"{effect} 효과를 {amount}만큼 바꾸기"

    # 감지: 키 눌림 체크
    elif opcode == "keyPressed:":
        key = interpret_block(block[1])
        return f"{key} 키가 눌렸는가?"

    # 감지: 마우스 위치 X
    elif opcode == "mouseX":
        return "마우스 X 위치"

    # 감지: 마우스 위치 Y
    elif opcode == "mouseY":
        return "마우스 Y 위치"

    # 감지: 스프라이트에 닿았는지?
    elif opcode == "touching:":
        target = interpret_block(block[1])
        return f"{target}에 닿았는가?"

    # 감지: 색깔 감지
    elif opcode == "color:sees:":
        color = interpret_block(block[1])
        return f"{color} 색깔을 감지했는가?"

    # 감지: 높이 센서 값 (예시)
    elif opcode == "timer":
        return "타이머 값"

    # 크기 설정
    elif opcode == "setSizeTo:":
        size = interpret_block(block[1])
        return f"크기를 {size}%로 설정하기"

    # 그래픽 효과 설정
    elif opcode == "setGraphicEffect:to:":
        effect = interpret_block(block[1])
        amount = interpret_block(block[2])
        return f"{effect} 효과를 {amount}로 설정하기"

    # 그래픽 효과 변경 (증가/감소)
    elif opcode == "changeGraphicEffect:by:":
        effect = interpret_block(block[1])
        amount = interpret_block(block[2])
        return f"{effect} 효과를 {amount}만큼 변경하기"

    # 특정 모습으로 바꾸기
    elif opcode == "lookLike:":
        costume_name = interpret_block(block[1])
        return f"모습을 '{costume_name}'(으)로 바꾸기"

    # 무한 반복 (doForever) : 내부 블록들 리스트
    # 제일 극혐
    elif opcode == "doForever":
        if args:
            inner_blocks = args[0]
            if isinstance(inner_blocks, list):
                inner_texts = [interpret_block(b) for b in inner_blocks]
                inner_text = "; ".join(inner_texts)
                return f"무한 반복하기: \n\t{inner_text}"
            else:
                return "무한 반복하기 (내부 블록 없음)"

    elif opcode == "doRepeat":
        if args and len(args) >= 2 and args[1]:
            repeat_count = interpret_block(args[0])  # 반복 횟수
            inner_blocks = args[1]  # 반복 내용
            inner_texts = [interpret_block(b) for b in inner_blocks]

            inner_text = "; ".join(inner_texts)
            return f"{repeat_count}번 반복하기: \n\t{inner_text}"
        else:
            return "반복하기 (인자 부족)"

    elif opcode == "doUntil":
        if args and len(args) >= 2:
            condition = interpret_block(args[0])
            inner_blocks = args[1]
            inner_texts = [interpret_block(b) for b in inner_blocks]

            inner_text = "; ".join(inner_texts)
            return f"{condition} 될 때까지 반복하기: \n\t{inner_text}"
        else:
            return "조건 반복 (인자 부족)"

    elif opcode == "doIf":
        if args and len(args) >= 2:
            condition = interpret_block(args[0])
            inner_blocks = args[1]
            inner_texts = [interpret_block(b) for b in inner_blocks]

            inner_text = "; ".join(inner_texts)
            return f"만약 {condition} 이면: \n\t{inner_text}"
        else:
            return "만약 조건문 (인자 부족)"

    elif opcode == "doIfElse":
        if args and len(args) >= 3:
            condition = interpret_block(args[0])
            if_block = args[1]
            else_block = args[2]
            if_texts = [interpret_block(b) for b in flatten_blocks(if_block)]
            else_texts = [interpret_block(b) for b in flatten_blocks(else_block)]
            return f"만약 {condition} 이면: \n\t{'; '.join(if_texts)}\n아니면: \n\t{'; '.join(else_texts)}"
        else:
            return "조건문 (if-else) (인자 부족)"

    elif opcode == "waitUntil":
        if args:
            condition = interpret_block(args[0])
            return f"{condition}이(가) 참이 될 때까지 기다리기"
        else:
            return "조건 없음: 기다리기"

    elif opcode == "foreverIf":
        if args:
            condition = interpret_block(args[0])
            if len(args) > 1 and args[1]:
                inner_blocks_flat = flatten_blocks(args[1])
                if inner_blocks_flat:
                    inner_texts = [interpret_block(b) for b in inner_blocks_flat]
                    inner_text = "; ".join(inner_texts)
                    return f"{condition}인 동안 계속 반복하기: \n\t{inner_text}"
                else:
                    return f"{condition}인 동안 계속 반복하기 (내부 블록 없음)"
            else:
                return f"{condition}인 동안 계속 반복하기 (내부 블록 없음)"
        else:
            return "조건 없음: 무한 반복"
        
    # 논리 연산: AND
    elif opcode == "&":
        left = interpret_block(block[1])
        right = interpret_block(block[2])
        return f"[{left} 그리고 {right}]"

    # 비교 연산: 같다
    elif opcode == "=":
        left = interpret_block(block[1])
        right = interpret_block(block[2])
        return f"[{left} = {right}]"

    # 문자열 길이
    elif opcode == "stringLength:":
        target = interpret_block(block[1])
        return f"[{target}의 길이]"

    # 비교 연산: 크다
    elif opcode == ">":
        left = interpret_block(block[1])
        right = interpret_block(block[2])
        return f"[{left} > {right}]"

    # 비교 연산: 작다
    elif opcode == "<":
        left = interpret_block(block[1])
        right = interpret_block(block[2])
        return f"[{left} < {right}]"

    # 리스트에 값 추가
    elif opcode == "append:toList:":
        item = interpret_block(block[1])
        lst = interpret_block(block[2])
        return f"[{lst}에 {item} 추가]"

    # 리스트 줄 수 세기
    elif opcode == "lineCountOfList:":
        lst = interpret_block(block[1])
        return f"[{lst}의 줄 수]"

    # 리스트에서 특정 줄 가져오기
    elif opcode == "getLine:ofList:":
        index = interpret_block(block[1])
        lst = interpret_block(block[2])
        return f"[{lst}의 {index}번째 줄]"

    # 사용자 입력값 또는 파라미터 획득
    elif opcode == "getParam":
        param_type = interpret_block(block[1])
        param_name = interpret_block(block[2])
        return f"{param_name}"   

    # 논리 연산: NOT
    elif opcode == "not":
        operand = interpret_block(block[1])
        return f"[{operand}이(가) 아니다]"

    # 산술 연산: 나머지 (%)
    elif opcode == "%":
        left = interpret_block(block[1])
        right = interpret_block(block[2])
        return f"[{left} 나누기 {right}의 나머지]"

    # 회전: 왼쪽으로 돌리기
    elif opcode == "turnLeft:":
        degrees = interpret_block(block[1])
        return f"[왼쪽으로 {degrees}도 회전]"

    # 이동: 앞으로 이동
    elif opcode == "forward:":
        steps = interpret_block(block[1])
        return f"[{steps} 만큼 움직이기]"

    # r: 입력값 or 랜덤값 의미할 수 있음 — 단순히 표현
    elif opcode == "r":
        param = interpret_block(block[1])
        return f"[{param} 매개변수]"  

    # 형 변환 등 기본 처리
    else:
        # 리스트 내 모든 원소를 재귀 처리 후 문자열로 합치기
        if isinstance(block, list):
            return "[" + ", ".join(interpret_block(b) for b in block) + "]"
        return str(block)


def flatten_blocks(blocks):
    if not isinstance(blocks, list):
        return []
    
    flattened = []
    for b in blocks:
        if isinstance(b, list):
            # 리스트 안에 리스트가 있을 경우 그대로 재귀적으로 보존
            flattened.append(b)
        else:
            flattened.append(b)
    return flattened

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


def clean_scripts(scripts):
    def clean_block(block):
        if isinstance(block, list):
            return [clean_block(b) for b in block if b is not None]
        return block if block is not None else "__EMPTY__"

    if not scripts:
        return []

    # 좌표 제거
    return [clean_block(blocks) for _, _, blocks in scripts]


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
    diff_messages = []

    for script_idx, (exp_blocks, act_blocks) in enumerate(zip(expected_scripts, actual_scripts)):
        for block_idx, (b_exp, b_act) in enumerate(zip(exp_blocks, act_blocks)):
            if not blocks_are_equivalent(b_exp, b_act):
                diff_positions = find_all_diff_elements(b_exp, b_act)
                diff_pos_str = ", ".join(diff_positions)
                diff_msg = (
                    f"<div style='margin-bottom: 1em;'>"
                    f"<strong>🎯 '{sprite_name}' 스프라이트 스크립트 {script_idx + 1}번 블록 {block_idx} 오류</strong><br>"
                    f"차이 위치: <code>{diff_pos_str}</code><br><br>"
                    f"<strong>✅ 정답:</strong><br>"
                    f"<pre style='background:#c8e6c9;padding:8px;border-radius:5px;'>{interpret_block(b_act)}</pre>"
                    f"<strong>❌ 제출:</strong><br>"
                    f"<pre style='background:#ffcdd2;padding:8px;border-radius:5px;'>{interpret_block(b_exp)}</pre>"
                    f"</div>"
                )
                diff_messages.append(diff_msg)

    return "<hr>".join(diff_messages) if diff_messages else ""

def compare_normalized_projects(s_project, a_project):
    errors = []
    diff_count = 0  # 차이난 블록 수 카운트

    s_sprites = {s["objName"]: s for s in s_project["sprites"]}
    a_sprites = {s["objName"]: s for s in a_project["sprites"]}

    all_names = set(s_sprites.keys()).union(a_sprites.keys())

    for name in sorted(all_names):
        # "보기블럭"은 채점에서 제외
        if name.replace(" ", "") in ["보기블럭", "보기블록"]:
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

        if not scripts_are_equivalent(s["scripts"], a["scripts"]):
            diff_html = make_diff_html(s["scripts"], a["scripts"], sprite_name=name)
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


def normalize_project_json(project_json):
    def extract_essential_sprite(sprite):
        return {
            "objName": sprite.get("objName"),
            "scripts": clean_scripts(sprite.get("scripts")),
            "costumes": sorted(
                [
                    {
                        "costumeName": c.get("costumeName", "") or "",
                        # "baseLayerMD5": c.get("baseLayerMD5", "") or "",
                    }
                    for c in sprite.get("costumes", [])
                    if c.get("costumeName") and c.get("baseLayerMD5")
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

    # Stage
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
                        "baseLayerMD5": c.get("baseLayerMD5", "") or "",
                    }
                    for c in project_json.get("costumes", [])
                    if c.get("costumeName") and c.get("baseLayerMD5")
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

    for submit_file in submission_dir.glob("*_제출.sb2"):
        base = normalize_name(submit_file.stem)

        # PDF 찾기
        pdf_path = submit_file.with_name(submit_file.stem.replace("_제출", "") + ".pdf")
        pdf_rel_path = pdf_path.name if pdf_path.exists() else None

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
            a_json = extract_json_from_sb2(matched_answer)

        except Exception as e:
            results.append({"오류내용": f"[project.json 추출 실패] {e}"})
            continue

        try:
            s_normalized = normalize_project_json(s_json)
            a_normalized = normalize_project_json(a_json)
        except Exception as e:
            print("▶ 정규화 중 예외 발생! 🔥")
            print("s_json keys:", s_json.keys())
            print("a_json keys:", a_json.keys())
            results.append({"오류내용": f"[정규화 실패] {e}"})
            continue

        try:
            pp = pprint.PrettyPrinter(indent=2, width=120, compact=False)
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
                        "문제PDF": pdf_rel_path,  # 🔍 추가된 항목
                    }
                )
            else:
                # 차이점 수집
                diff_errors = compare_normalized_projects(s_normalized, a_normalized)
                print(f"diff_errors: {diff_errors}")
                results.append(
                    {
                        "제출": submit_file.name,
                        "제출파일경로": str(submit_file),  # ✅ 여기 추가
                        "정답": matched_answer.name,
                        "정답여부": "X",
                        "오류내용": "; ".join(diff_errors),
                        "문제PDF": pdf_rel_path,  # 🔍 추가된 항목
                    }
                )
        except Exception as e:
            results.append(
                {
                    "제출": submit_file.name,
                    "제출파일경로": str(submit_file),  # ✅ 여기 추가
                    "정답": matched_answer.name,
                    "정답여부": "오류",
                    "오류내용": f"[normalize or compare 중 오류] {e}",
                    "문제PDF": pdf_rel_path,  # 🔍 추가된 항목
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