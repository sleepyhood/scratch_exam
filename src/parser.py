BLOCK_CLASS_MAP = {
    #
    # 동작
    "forward:": "cmd-motion",
    "turnRight:": "cmd-motion",
    "xpos": "cmd-motion",
    "ypos": "cmd-motion",
    #
    # 모양
    "nextCostume": "cmd-looks",
    "lookLike:": "cmd-looks",
    "costumeIndex": "cmd-looks",
    #
    # 소리
    "playSound:": "cmd-sound",
    #
    # 이벤트
    "broadcast:": "cmd-events",
    "doBroadcastAndWait": "cmd-events",
    #
    # 제어
    "doForever": "cmd-control",
    "doIf": "cmd-control",
    "doIfElse": "cmd-control",
    #
    # 연산
    "+": "cmd-operators",
    "-": "cmd-operators",
    "*": "cmd-operators",
    "/": "cmd-operators",
    "%": "cmd-operators",
    "=": "cmd-operators",
    "<": "cmd-operators",
    ">": "cmd-operators",
    "&": "cmd-operators",
    "|": "cmd-operators",
    #
    # 감지
    "mousePressed": "cmd-sensing",
    "touching:": "cmd-sensing",
    "color:sees:": "cmd-sensing",
    "answer": "cmd-sensing",
    "keyPressed:": "cmd-sensing",
    #
    # 변수
    "setVar:to:": "cmd-data",
    "readVariable": "cmd-data",
    # 필요시 더 추가
}


# 피연산자가 올바른 수식인지 확인
def isCorrectOperand(left, right):
    left = "(코드 없음)" if left == "" else left
    right = "(코드 없음)" if right == "" else right
    return left, right


def interpret_block(block, depth=0, highlight_paths=None, current_path=None):
    indent = "  " * depth

    if not isinstance(block, list):
        return str(block)

    opcode = block[0]

    # 인자 확인
    # 1번 인덱스 없이 제출된 경우도 존재할 수 있다. (반복문에 조건이 없다던지...)
    args = block[1:] if len(block) > 1 else []

    # 틀린 부분 강조
    if current_path is None:
        current_path = []

    # 지금 이 경로가 강조 대상인지 확인
    is_highlighted = highlight_paths and current_path in highlight_paths
    css_class = BLOCK_CLASS_MAP.get(opcode, "cmd-additional")
    if is_highlighted:
        css_class += " block-error"

    # 변수 설정
    if opcode == "setVar:to:":
        if len(block) >= 3:
            var_name = interpret_block(
                block[1], depth, highlight_paths, current_path + [1]
            )
            expr = interpret_block(block[2], depth, highlight_paths, current_path + [2])
            return (
                f"<span class='{css_class}'>{var_name}를 {expr}으로 정하기</span></br>"
            )
        else:
            return f"<span class='{css_class}'>변수 설정 블록 (인자 부족)</span></br>"

    # 변수 값 읽기
    elif opcode == "readVariable":
        var_name = block[1]
        return f"<span class='{css_class}'>{var_name}</span>"

    # 연산: 더하기
    elif opcode == "+":
        left = interpret_block(block[1])
        right = interpret_block(block[2])
        left, right = isCorrectOperand(left, right)

        return f"<span class='{css_class}'>{left} + {right}</span>"

    # 연산: 빼기
    elif opcode == "-":
        left = interpret_block(block[1])
        right = interpret_block(block[2])
        left, right = isCorrectOperand(left, right)

        return f"<span class='{css_class}'>{left} - {right}</span>"

    # 연산: 곱하기
    elif opcode == "*":
        left = interpret_block(block[1])
        right = interpret_block(block[2])
        left, right = isCorrectOperand(left, right)

        return f"<span class='{css_class}'>{left} * {right}</span>"

    # 연산: 나누기
    elif opcode == "/":
        left = interpret_block(block[1])
        right = interpret_block(block[2])
        left, right = isCorrectOperand(left, right)

        return f"<span class='{css_class}'>{left} / {right}</span>"

    # 난수 생성 (min ~ max)
    elif opcode == "randomFrom:to:":
        min_val = interpret_block(block[1])
        max_val = interpret_block(block[2])
        return f"<span class='{css_class}'>{min_val}부터 {max_val}사이의 난수</span>"

    # 위치 설정
    elif opcode == "gotoX:y:":
        x = interpret_block(block[1])
        y = interpret_block(block[2])
        return (
            f"<span class='{css_class}'>x 좌표 {x}, y 좌표 {y}로 이동하기</span><br/>"
        )

    # 방향 설정
    elif opcode == "pointInDirection:":
        direction = interpret_block(block[1])
        return f"<span class='{css_class}'>방향을 {direction}도로 설정하기</span></br>"

    elif opcode == "xpos":
        return f"<span class='{css_class}'>x좌표</span>"

    elif opcode == "ypos":
        return f"<span class='{css_class}'>y좌표</span>"

    elif opcode == "doBroadcastAndWait":
        if args:
            return (
                f"<span class='{css_class}'>{args[0]} 신호 보내고 기다리기</span><br/>"
            )
        else:
            return f"<span class='{css_class}'>신호 보내고 기다리기 (신호 없음)</span><br/>"

    elif opcode == "broadcast:":
        if args:
            return f"<span class='{css_class}'>{args[0]} 신호 보내기</span><br/>"
        else:
            return f"<span class='{css_class}'>신호 보내기 (신호 없음)</span><br/>"

    # 변수 값 증가
    elif opcode == "changeVar:by:":
        var_name = block[1]
        delta = interpret_block(block[2])
        return f"<span class='{css_class}'>{var_name}를 {delta}만큼 더하기</span><br/>"

    # 이벤트: 시작했을 때
    elif opcode == "whenGreenFlag":
        return "초록 깃발 클릭했을 때"

    # 이벤트: 스프라이트 클릭했을 때
    elif opcode == "whenClicked":
        return "스프라이트 클릭했을 때"

    # 제어: 반복 (횟수)
    elif opcode == "repeat:times:":
        times = interpret_block(block[1])
        return f"{times}번 반복하기:"

    # 제어: 만약 ~ 이면
    # elif opcode == "if:":
    #     condition = interpret_block(block[1])
    #     return (
    #         f"{indent}<span class='{css_class}'>만약 {condition}이면:\n\t"
    #         + "\n</span>".join(
    #             {indent} + interpret_block(b, depth + 1) for b in inner_blocks
    #         )
    #     )

    # 제어: 만약 ~ 이고 아니면
    # elif opcode == "if:else:":
    #     condition = interpret_block(block[1])
    #     return f"만약 {condition}이면, 아니면"

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

    # 감지: 키 눌림 체크
    elif opcode == "keyPressed:":
        key = interpret_block(block[1])
        return f"<span class='{css_class}'>{key} 키가 눌렸는가?</span>"

    # 감지: 마우스 위치 X
    elif opcode == "mouseX":
        return "마우스 X 위치"

    # 감지: 마우스 위치 Y
    elif opcode == "mouseY":
        return "마우스 Y 위치"

    # 감지: 스프라이트에 닿았는지?
    elif opcode == "touching:":
        target = interpret_block(block[1])
        return f"<span class='{css_class}'>{target}에 닿았는가?</span>"

    # 감지: 색깔 감지
    elif opcode == "color:sees:":
        color = interpret_block(block[1])
        return f"<span class='{css_class}'>{color} 색깔을 감지했는가?</span>"

    # 감지: 높이 센서 값 (예시)
    elif opcode == "timer":
        return "(타이머)"

    # 감지: 대답
    elif opcode == "answer":
        return "(대답)"

    # 크기 설정
    elif opcode == "setSizeTo:":
        size = interpret_block(block[1])
        return f"<span class='{css_class}'>크기를 {size}%로 설정하기</span><br/>"

    # 그래픽 효과 설정
    elif opcode == "setGraphicEffect:to:":
        effect = interpret_block(block[1])
        amount = interpret_block(block[2])
        return (
            f"<span class='{css_class}'>{effect} 효과를 {amount}로 설정하기</span><br/>"
        )

    # 그래픽 효과 변경 (증가/감소)
    elif opcode == "changeGraphicEffect:by:":
        effect = interpret_block(block[1])
        amount = interpret_block(block[2])
        return f"<span class='{css_class}'>{effect} 효과를 {amount}만큼 변경하기</span><br/>"

    # 특정 모습으로 바꾸기
    elif opcode == "lookLike:":
        costume_name = interpret_block(block[1])
        return f"<span class='{css_class}'>모습을 '{costume_name}'(으)로 바꾸기</span><br/>"

    elif opcode == "nextCostume":
        return f"<span class='{css_class}'>다음 모양으로 바꾸기</span><br/>"

    elif opcode == "costumeIndex":
        return f"<span class='{css_class}'>모양 번호</span>"

    elif opcode == "doForever":
        if args:
            inner_blocks = args[0]
            if isinstance(inner_blocks, list):
                inner_texts = [
                    interpret_block(b, depth + 1) or "" for b in inner_blocks
                ]
                inner_html = "\n".join(inner_texts)

                return (
                    f"{'  ' * depth}<div class='block-wrapper cmd-control'>\n"
                    f"{'  ' * (depth + 1)}<div class='block-header'>무한 반복하기</div>\n"
                    f"{'  ' * (depth + 1)}<div class='block-body'>\n"
                    f"{inner_html}\n"
                    f"{'  ' * (depth + 1)}</div>\n"
                    f"{'  ' * depth}</div>"
                )
            else:
                return f"{'  ' * depth}<span class='cmd-control'>무한 반복하기 (내부 블록 없음)</span>"
        else:
            return f"{'  ' * depth}<span class='cmd-control'>무한 반복하기 (코드 없음)</span>"

    elif opcode == "doRepeat":
        if args and len(args) >= 2 and args[1]:
            repeat_count = interpret_block(args[0])  # 반복 횟수
            inner_blocks = args[1]  # 반복 내용
            inner_texts = [interpret_block(b) or "" for b in inner_blocks]

            # inner_text = "\n ".join(inner_texts)
            inner_text = "\n".join("  " * (depth + 1) + t for t in inner_texts)

            return f"{'  ' * depth}{repeat_count}번 반복하기:\n{inner_text}"
        else:
            return f"{'  ' * depth}반복하기 (코드 없음)"

    elif opcode == "doUntil":
        if args and len(args) >= 2:
            condition = interpret_block(args[0])
            inner_blocks = args[1]
            inner_texts = [interpret_block(b) or "" for b in inner_blocks]

            if inner_texts:
                # inner_text = "\n\t" + "\n\t".join(inner_texts)
                inner_text = "\n".join("  " * (depth + 1) + t for t in inner_texts)

            else:
                inner_text = "\n".join("  " * (depth + 1) + "<내용 없음>")

            return (
                f"{'  ' * depth}<div class='block-wrapper cmd-control'>\n"
                f"{'  ' * (depth + 1)}<div class='block-header'>{condition} 될 때까지 반복하기:\n</div>\n"
                f"{'  ' * (depth + 1)}<div class='block-body'>\n"
                f"{inner_text}\n"
                f"{'  ' * (depth + 1)}</div>\n"
                f"{'  ' * depth}</div>"
            )
        else:
            return f"{'  ' * depth}조건 반복 (코드 없음)"

    elif opcode == "doIf":
        if args and len(args) >= 2:
            condition = interpret_block(args[0])
            inner_blocks = args[1]
            inner_texts = [interpret_block(b) or "" for b in inner_blocks]

            # inner_text = "\n ".join(inner_texts)
            inner_text = "\n".join("  " * (depth + 1) + t for t in inner_texts)

            return (
                f"{'  ' * depth}<div class='block-wrapper cmd-control'>\n"
                f"{'  ' * (depth + 1)}<div class='block-header'>만약 {condition} 라면</div>\n"
                f"{'  ' * (depth + 1)}<div class='block-body'>\n"
                f"{inner_text}\n"
                f"{'  ' * (depth + 1)}</div>\n"
                f"{'  ' * depth}</div>"
                # f"{'  ' * depth}<span class='{css_class}'>만약 {condition} 라면:</span>\n{inner_text}"
            )

        else:
            return f"{'  ' * depth}<span class='{css_class}'>만약 조건문 (코드 없음)</span>"

    elif opcode == "doIfElse":
        if args and len(args) >= 3:
            condition = interpret_block(args[0], depth)
            if_block = args[1]
            else_block = args[2]
            if_texts = [
                interpret_block(b, depth + 1) or "" for b in flatten_blocks(if_block)
            ]
            else_texts = [
                interpret_block(b, depth + 1) or "" for b in flatten_blocks(else_block)
            ]

            def add_indent(texts):
                return "\n".join(
                    "  " * (depth + 1) + line
                    for text in texts
                    for line in text.splitlines()
                )

            if_part = add_indent(if_texts)
            else_part = add_indent(else_texts)

            return f"{'  ' * depth}만약 {condition} 라면:\n{if_part}\n{'  ' * depth}아니면:\n{else_part}"
        else:
            return f"{'  ' * depth}조건문 (if-else) (코드 없음)"

    elif opcode == "waitUntil":
        if args:
            condition = interpret_block(args[0])
            return f"{condition}이(가) 참이 될 때까지 기다리기"
        else:
            return "조건 없음: 기다리기"

    # elif opcode == "foreverIf":
    #     if args:
    #         condition = interpret_block(args[0])
    #         if len(args) > 1 and args[1]:
    #             inner_blocks_flat = flatten_blocks(args[1])
    #             if inner_blocks_flat:
    #                 inner_texts = [interpret_block(b) or "" for b in inner_blocks_flat]
    #                 # inner_text = "\n ".join(inner_texts)
    #                 inner_text = "\n".join("  " * (depth + 1) + t for t in inner_texts)

    #                 return f"{'  ' * depth}{condition}인 동안 계속 반복하기:\n{inner_text}"
    #             else:
    #                 return f"{'  ' * depth}{condition}인 동안 계속 반복하기 (내부 블록 없음)"
    #         else:
    #             return (
    #                 f"{'  ' * depth}{condition}인 동안 계속 반복하기 (내부 블록 없음)"
    #             )
    #     else:
    #         return f"{'  ' * depth}조건 없음: 무한 반복"

    # 논리 연산: AND
    elif opcode == "&":
        left = interpret_block(block[1])
        right = interpret_block(block[2])
        left, right = isCorrectOperand(left, right)

        return f"<span class='{css_class}'>{left} 그리고 {right}</span>"

    elif opcode == "|":  # 또는?
        left = interpret_block(block[1])
        right = interpret_block(block[2])
        left, right = isCorrectOperand(left, right)

        return f"<span class='{css_class}'>{left} 또는 {right}</span>"

    # 비교 연산: 같다
    elif opcode == "=":
        left = interpret_block(block[1], depth, highlight_paths, current_path + [1])
        right = interpret_block(block[2], depth, highlight_paths, current_path + [2])
        left, right = isCorrectOperand(left, right)
        return f"<span class='{css_class}'>{left} = {right}</span>"

    # 문자열 길이
    elif opcode == "stringLength:":
        target = interpret_block(block[1])
        return f"[{target}의 길이]"

    # 비교 연산: 크다
    elif opcode == ">":
        left = interpret_block(block[1])
        right = interpret_block(block[2])
        left, right = isCorrectOperand(left, right)

        return f"[{left}이 {right}보다 크다]"

    # 비교 연산: 작다
    elif opcode == "<":
        left = interpret_block(block[1])
        right = interpret_block(block[2])
        left, right = isCorrectOperand(left, right)

        return f"<span class='{css_class}'>{left} < {right}</span>"

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
        return f"({lst}의 {index}번째 줄)"

    # 사용자 입력값 또는 파라미터 획득
    elif opcode == "getParam":
        param_type = interpret_block(block[1])
        param_name = interpret_block(block[2])
        return f"{param_name}"

    # 논리 연산: NOT
    elif opcode == "not":
        operand = interpret_block(block[1])
        return f"({operand}이(가) 아니다)"

    # 산술 연산: 나머지 (%)
    elif opcode == "%":
        left = interpret_block(block[1])
        right = interpret_block(block[2])
        return f"<span class='{css_class}'>({left} 나누기 {right}의 나머지)</span>"

    # 회전: 왼쪽으로 돌리기
    elif opcode == "turnLeft:":
        degrees = interpret_block(block[1])
        return f"<span class='{css_class}'>왼쪽으로 {degrees}도 회전</span><br/>"

    # 이동: 앞으로 이동
    elif opcode == "forward:":
        steps = interpret_block(block[1])
        # return f"[({steps}) 만큼 움직이기]"
        return f"<span class='{css_class}'>{steps} 만큼 움직이기</span><br/>"

        # return span(f"{steps} 만큼 움직이기", "cmd-motion")

    # r: 입력값 or 랜덤값 의미할 수 있음 — 단순히 표현
    elif opcode == "r":
        param = interpret_block(block[1])
        return f"{param} 매개변수"

    # 형 변환 등 기본 처리
    else:
        # 리스트 내 모든 원소를 재귀 처리 후 문자열로 합치기
        if isinstance(block, list):
            return "[" + ", ".join(interpret_block(b) or "" for b in block) + "]"
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
