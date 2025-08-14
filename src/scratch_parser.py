BLOCK_CLASS_MAP = {
    #
    # 동작
    "forward:": "cmd-motion",
    "turnLeft:": "cmd-motion",
    "turnRight:": "cmd-motion",
    "xpos": "cmd-motion",
    "ypos": "cmd-motion",
    "heading": "cmd-motion",
    "heading:": "cmd-motion",
    "gotoX:y:": "cmd-motion",
    "ypos:": "cmd-motion",
    "xpos:": "cmd-motion",
    "changeYposBy:": "cmd-motion",
    "changeXposBy:": "cmd-motion",
    "gotoSpriteOrMouse:": "cmd-motion",
    "bounceOffEdge": "cmd-motion",
    "setRotationStyle": "cmd-motion",
    "glideSecs:toX:y:elapsed:from:": "cmd-motion",
    "pointTowards:": "cmd-motion",
    #
    # 형태
    "nextCostume": "cmd-looks",
    "lookLike:": "cmd-looks",
    "costumeIndex": "cmd-looks",
    "say:duration:elapsed:from:": "cmd-looks",
    "say:": "cmd-looks",
    "think:duration:elapsed:from:": "cmd-looks",
    "think:": "cmd-looks",
    "show": "cmd-looks",
    "hide": "cmd-looks",
    "scale": "cmd-looks",
    "sceneName": "cmd-looks",
    "changeSizeBy:": "cmd-looks",
    "goBackByLayers:": "cmd-looks",
    "comrToFront": "cmd-looks",
    "startScene":  "cmd-looks",

    #
    # 소리
    "playSound:": "cmd-sound",
    #
    # 이벤트
    "broadcast:": "cmd-events",
    "doBroadcastAndWait": "cmd-events",
    "whenSensorGreaterThan": "cmd-events",
    "whenCloned": "cmd-events",
    #
    # 제어
    "doForever": "cmd-control",
    "doIf": "cmd-control",
    "doIfElse": "cmd-control",
    "wait:elapsed:from:": "cmd-control",
    "doWaitUntil": "cmd-control",
    "stopScripts": "cmd-control",
    "deleteClone": "cmd-control",
    "createCloneOf": "cmd-control",
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
    "not": "cmd-operators",
    "stringLength:": "cmd-operators",
    "letter:of:": "cmd-operators",
    "concatenate:with:": "cmd-operators",
    "rounded": "cmd-operators",
    "computeFunction:of:": "cmd-operators",
    "randomFrom:to:": "cmd-operators",
    #
    # 감지
    "mousePressed": "cmd-sensing",
    "touching:": "cmd-sensing",
    "touchingColor:": "cmd-sensing",
    "color:sees:": "cmd-sensing",
    "answer": "cmd-sensing",
    "timer": "cmd-sensing",
    "keyPressed:": "cmd-sensing",
    "distanceTo:": "cmd-sensing",
    "getUserName": "cmd-sensing",
    "timestamp": "cmd-sensing",
    "mouseX": "cmd-sensing",
    "mouseY": "cmd-sensing",
    "setVideoState": "cmd-sensing",
    "getAttribute:of:": "cmd-sensing",
    "timeAndDate": "cmd-sensing",
    #
    # 데이터 - 변수
    "setVar:to:": "cmd-data",
    "readVariable": "cmd-data",
    "changeVar:by:": "cmd-data",
    "showVariable:": "cmd-data",
    "hideVariable:": "cmd-data",
    #
    # 데이터 - 리스트
    "append:toList:": "cmd-list",
    "deleteLine:ofList:": "cmd-list",
    "insert:at:ofList:": "cmd-list",
    "showList:": "cmd-list",
    "hideList:": "cmd-list",
    "setLine:ofList:to:": "cmd-list",
    "lineCountOfList:": "cmd-list",
    "list:contains:": "cmd-list",
    "getLine:ofList:": "cmd-list",
    #
    # 추가 블록
    "call": "cmd-additional",
    "getParam": "cmd-additional",
    # 필요시 더 추가
}


# 피연산자가 올바른 수식인지 확인
def isCorrectOperand(left, right):
    left = "(코드 없음)" if left == "" else left
    right = "(코드 없음)" if right == "" else right
    return left, right


# 상수는 다르게 표시
def highlight_if_constant(val, raw):
    if isinstance(raw, (int, float)) or (
        isinstance(raw, str) and raw.replace(".", "", 1).replace("-", "", 1).isdigit()
    ):
        return f"<span class='constant-highlight'>{val}</span>"

    # 문자열이면서 다른 블럭(span)으로 감싸지 않은 경우
    if isinstance(val, str) and not val.startswith("<span class="):
        return f"<span class='constant-highlight'>{val}</span>"

    return val


def highlight_if_color(val, raw):
    if isinstance(raw, (int, float)) or (
        isinstance(raw, str) and raw.replace(".", "", 1).replace("-", "", 1).isdigit()
    ):
        # 색상으로 표현 가능한 범위인지 확인 (24bit: 0~16777215)
        num = int(raw)
        if 0 <= num <= 16777215:
            hex_color = f"{num:06x}"
            return f"<span class='color-box' style='background-color:#{hex_color}' title='#{hex_color}'></span>"
        else:
            return f"<span class='constant-highlight'>{val}</span>"


def is_path_highlighted(current_path, highlight_paths):
    return any(current_path == path for path in highlight_paths or [])


def interpret_block(block, depth=0, highlight_paths=None, current_path=None):
    indent = "  " * depth

    if not isinstance(block, list):
        # 원시값일 경우에도 경로가 강조 대상이면 감쌈
        # if is_path_highlighted(current_path, highlight_paths):
        #     return f"<span class='block-error'>{block}</span>"
        return str(block)

    # ✅ 빈 리스트 방어
    if not block:
        return "[빈 블록]"

    opcode = block[0]
    # print(f"highlight_paths: {highlight_paths}\n")
    # 인자 확인
    # 1번 인덱스 없이 제출된 경우도 존재할 수 있다. (반복문에 조건이 없다던지...)
    args = block[1:] if len(block) > 1 else []

    # 틀린 부분 강조
    # if current_path is None:
    #     current_path = []

    # 지금 이 경로가 강조 대상인지 확인
    css_class = BLOCK_CLASS_MAP.get(opcode, "cmd-additional")
    # if is_path_highlighted(current_path, highlight_paths):
    #     css_class += " block-error"

    # 변수 설정
    if opcode == "setVar:to:":
        if len(block) >= 3:
            var_name = block[1]
            expr_raw = block[2]
            expr = interpret_block(block[2])

            expr_disp = highlight_if_constant(expr, expr_raw)

            return f"<span class='{css_class}'>{var_name}를 {expr_disp} 으로 정하기</span></br>"
        else:
            return f"<span class='{css_class}'>변수 설정 블록 (인자 부족)</span></br>"

    # 변수 값 읽기
    elif opcode == "readVariable":
        var_name = interpret_block(args[0], depth)
        return f"<span class='{css_class}'>{var_name}</span>"

    # 연산: 더하기
    elif opcode == "+":
        left_raw = block[1]
        right_raw = block[2]

        left = interpret_block(block[1])
        right = interpret_block(block[2])
        left, right = isCorrectOperand(left, right)

        left_disp = highlight_if_constant(left, left_raw)
        right_disp = highlight_if_constant(right, right_raw)

        return f"<span class='{css_class}'>{left_disp} + {right_disp}</span>"

    # 연산: 빼기
    elif opcode == "-":
        left_raw = block[1]
        right_raw = block[2]

        left = interpret_block(block[1])
        right = interpret_block(block[2])
        left, right = isCorrectOperand(left, right)

        left_disp = highlight_if_constant(left, left_raw)
        right_disp = highlight_if_constant(right, right_raw)

        return f"<span class='{css_class}'>{left_disp} - {right_disp}</span>"

    # 연산: 곱하기
    elif opcode == "*":
        left_raw = block[1]
        right_raw = block[2]

        left = interpret_block(block[1])
        right = interpret_block(block[2])
        left, right = isCorrectOperand(left, right)

        left_disp = highlight_if_constant(left, left_raw)
        right_disp = highlight_if_constant(right, right_raw)

        return f"<span class='{css_class}'>{left_disp} * {right_disp}</span>"

    # 연산: 나누기
    elif opcode == "/":
        left_raw = block[1]
        right_raw = block[2]

        left = interpret_block(block[1])
        right = interpret_block(block[2])
        left, right = isCorrectOperand(left, right)

        left_disp = highlight_if_constant(left, left_raw)
        right_disp = highlight_if_constant(right, right_raw)

        return f"<span class='{css_class}'>{left_disp} / {right_disp}</span>"

    # 난수 생성 (min ~ max)
    elif opcode == "randomFrom:to:":
        left_raw = block[1]
        right_raw = block[2]

        left = interpret_block(block[1])
        right = interpret_block(block[2])
        left, right = isCorrectOperand(left, right)

        left_disp = highlight_if_constant(left, left_raw)
        right_disp = highlight_if_constant(right, right_raw)

        return (
            f"<span class='{css_class}'>{left_disp}부터 {right_disp}사이의 난수</span>"
        )

    # 위치 설정
    elif opcode == "gotoX:y:":
        x_raw = block[1]
        y_raw = block[2]
        x = interpret_block(x_raw)
        y = interpret_block(y_raw)

        x_disp = highlight_if_constant(x, x_raw)
        y_disp = highlight_if_constant(y, y_raw)
        return f"<span class='{css_class}'>x 좌표 {x_disp}, y 좌표 {y_disp}로 이동하기</span><br/>"

    elif opcode == "heading:":
        direction_raw = block[1]
        direction = interpret_block(direction_raw)
        direction_disp = highlight_if_constant(direction, direction_raw)
        return f"<span class='{css_class}'>{direction_disp}도 방향 보기</span><br/>"

    elif opcode == "ypos:":
        cood = interpret_block(block[1])
        cood_disp = highlight_if_constant(cood, block[1])
        return f"<span class='{css_class}'>y좌표를 {cood_disp}(으)로 정하기</span><br/>"

    elif opcode == "changeYposBy:":
        cood = interpret_block(block[1])
        cood_disp = highlight_if_constant(cood, block[1])
        return f"<span class='{css_class}'>y좌표를 {cood_disp}만큼 바꾸기</span><br/>"

    elif opcode == "xpos:":
        cood = interpret_block(block[1])
        cood_disp = highlight_if_constant(cood, block[1])
        return f"<span class='{css_class}'>x좌표를 {cood_disp}(으)로 정하기</span><br/>"
    elif opcode == "changeXposBy:":
        cood = interpret_block(block[1])
        cood_disp = highlight_if_constant(cood, block[1])
        return f"<span class='{css_class}'>x좌표를 {cood_disp}만큼 바꾸기</span><br/>"

    # 방향 설정
    elif opcode == "pointInDirection:":
        direction_raw = block[1]
        direction = interpret_block(block[1])
        direction_disp = highlight_if_constant(direction, direction_raw)
        return f"<span class='{css_class}'>방향을 {direction_disp}도로 설정하기</span></br>"

    elif opcode == "xpos":
        return f"<span class='{css_class}'>x좌표</span>"

    elif opcode == "ypos":
        return f"<span class='{css_class}'>y좌표</span>"

    elif opcode == "heading":
        return f"<span class='{css_class}'>방향</span>"

    elif opcode == "bounceOffEdge":
        return f"<span class='{css_class}'>벽에 닿으면 튕기기</span><br/>"

    elif opcode == "setRotationStyle":
        set_type = block[1]
        return f"<span class='{css_class}'>회전 방식을 {set_type}로 정하기</span><br/>"

    elif opcode == "glideSecs:toX:y:elapsed:from:":
        duration = interpret_block(block[1])
        x = interpret_block(block[2])
        y = interpret_block(block[3])

        duration_disp = highlight_if_constant(duration, block[1])
        x_disp = highlight_if_constant(x, block[2])
        y_disp = highlight_if_constant(y, block[3])

        return f"<span class='{css_class}'>{duration_disp} 초 동안 x: {x_disp} y: {y_disp} 으로 이동하기</span><br/>"

    elif opcode == "pointTowards:":
        destination = interpret_block(block[1])
        destination = (
            "마우스 포인터"
            if destination == "_mouse_"
            else "랜덤 위치" if destination == "_random_" else destination
        )
        return f"<span class='{css_class}'>{destination} 쪽 보기</span><br/>"

    elif opcode == "doBroadcastAndWait":
        if args:
            return f"<span class='{css_class}'>{args[0]} 방송하고 기다리기</span><br/>"
        else:
            return (
                f"<span class='{css_class}'>방송하고 기다리기 (신호 없음)</span><br/>"
            )

    elif opcode == "broadcast:":
        if args:
            return f"<span class='{css_class}'>{args[0]} 방송하기</span><br/>"
        else:
            return f"<span class='{css_class}'>방송하기 (신호 없음)</span><br/>"

    # 변수 값 증가
    elif opcode == "changeVar:by:":

        var_name = block[1]
        delta_raw = block[2]
        delta = interpret_block(block[2])

        delta_disp = highlight_if_constant(delta, delta_raw)
        return f"<span class='{css_class}'>{var_name}를 {delta_disp}만큼 바꾸기</span><br/>"

    elif opcode == "showVariable:":
        value = block[1]
        return f"<span class='{css_class}'>{value} 변수 보이기</span><br/>"

    elif opcode == "hideVariable:":
        value = block[1]
        return f"<span class='{css_class}'>{value} 변수 숨기기</span><br/>"

    # 이벤트: 시작했을 때
    elif opcode == "whenGreenFlag":
        return f"<span class='block roof-block'>🏳️ 클릭했을 때</span><br/>"

    # 이벤트: 스프라이트 클릭했을 때
    elif opcode == "whenClicked":
        return f"<span class='block roof-block'>이 스프라이트가 클릭될 때</span><br/>"

    elif opcode == "whenIReceive":
        value = block[1]
        return f"<span class='block roof-block'>{value} 을(를) 받았을 때</span><br/>"

    elif opcode == "whenKeyPressed":
        value = block[1]
        return f"<span class='block roof-block'>{value} 키를 눌렀을 때</span><br/>"

    # 이벤트: 볼륨 > 10
    elif opcode == "whenSensorGreaterThan":
        event_type = block[1]
        value_raw = block[2]
        value = interpret_block(block[2])
        value_raw_disp = highlight_if_constant(value, value_raw)

        return f"<span class='block roof-block'>{event_type} > {value_raw_disp} 일 때</span><br/>"

    # 이벤트: 복제되었을 때
    elif opcode == "whenCloned":
        return f"<span class='block roof-block'>복제되었을 때</span><br/>"

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
        times_raw = block[1]
        times = interpret_block(block[1])
        times_disp = highlight_if_constant(times, times_raw)
        return f"<span class='{css_class}'>{times_disp}초 기다리기</span><br/>"

    elif opcode == "doWaitUntil":
        condition = interpret_block(block[1])
        return f"<span class='{css_class}'>{condition} 까지 기다리기</span><br/>"

    elif opcode == "stopScripts":
        option = block[1]
        option_disp = (
            "이 스크립트"
            if option == "this script"
            else (
                "스프라이트에 있는 다른 스크립트"
                if option == "other scripts in sprite"
                else "모두"
            )
        )
        return f"<span class='{css_class}'>{option_disp} 멈추기</span><br/>"

    # 감지: 키 눌림 체크
    elif opcode == "keyPressed:":
        key = interpret_block(block[1])
        return f"<span class='{css_class}'>{key} 키가 눌렸는가?</span>"

    elif opcode == "mousePressed":
        return f"<span class='{css_class}'>마우스를 클릭했는가?</span>"

    elif opcode == "distanceTo:":
        destination = block[1]
        destination = "마우스 포인터" if destination == "_mouse_" else destination
        return f"<span class='{css_class}'>{destination}까지의 거리</span>"

    elif opcode == "getUserName":
        return f"<span class='{css_class}'>사용자 이름</span>"

    elif opcode == "timestamp":
        return f"<span class='{css_class}'>2000년 이후 현재까지 날짜수</span>"

    # 감지: 마우스 위치 X
    elif opcode == "mouseX":
        return f"<span class='{css_class}'>마우스의 X좌표</span>"

    # 감지: 마우스 위치 Y
    elif opcode == "mouseY":
        return f"<span class='{css_class}'>마우스의 y좌표</span>"

    elif opcode == "setVideoState":
        state = block[1]

    # 왜 안됨???
    # return f"<span class='{css_class}'>비디오 {"켜기" if state == "on" else "끄기"}</span>"

    elif opcode == "getAttribute:of:":
        option = block[1]
        option = (
            "x좌표"
            if option == "x position"
            else "y좌펴" if option == "y position" else option
        )
        sprite = interpret_block(block[2])

        return f"<span class='{css_class}'>{option} of {sprite}</span>"

    # 감지: 스프라이트에 닿았는지?
    elif opcode == "touching:":
        target = interpret_block(block[1])
        target = "벽" if target == "_edge_" else target
        return f"<span class='{css_class}'>{target}에 닿았는가?</span>"

    # 감지: 색깔 감지
    elif opcode == "touchingColor:":
        color_raw = block[1]
        color = interpret_block(block[1])
        color_disp = highlight_if_color(color, color_raw)
        return f"<span class='{css_class}'>{color_disp} 색에 닿았는가?</span>"

    # 감지: 색깔1이 색깔2 감지
    elif opcode == "color:sees:":
        color1 = interpret_block(block[1])
        color_disp1 = highlight_if_color(color1, block[1])

        color2 = interpret_block(block[2])
        color_disp2 = highlight_if_color(color2, block[2])
        return f"<span class='{css_class}'>{color_disp1} 색이 {color_disp2} 색에 닿았는가?</span>"

    # 감지: 높이 센서 값 (예시)
    elif opcode == "timer":

        return f"<span class='{css_class}'>타이머</span>"

    # 감지: 대답
    elif opcode == "answer":
        return f"<span class='{css_class}'>대답</span>"

    # 형태: 의상 바꾸기
    elif opcode == "switchCostumeTo:":
        costume = interpret_block(block[1])
        return f"의상을 {costume}(으)로 바꾸기"

    # 크기 설정
    elif opcode == "setSizeTo:":
        size_raw = block[1]
        size = interpret_block(block[1])
        size_disp = highlight_if_constant(size, size_raw)
        return f"<span class='{css_class}'>크기를 {size_disp}(으)로 정하기</span><br/>"

    # 그래픽 효과 설정
    elif opcode == "setGraphicEffect:to:":
        effect = interpret_block(block[1])
        amount_raw = block[2]
        amount = interpret_block(block[2])
        amount_disp = highlight_if_constant(amount, amount_raw)

        return f"<span class='{css_class}'>{effect} 효과를 {amount_disp}(으)로 정하기</span><br/>"

    # 그래픽 효과 변경 (증가/감소)
    elif opcode == "changeGraphicEffect:by:":
        effect = interpret_block(block[1])
        amount_raw = block[2]
        amount = interpret_block(block[2])
        amount_disp = highlight_if_constant(amount, amount_raw)

        return f"<span class='{css_class}'>{effect} 효과를 {amount_disp}만큼 바꾸기</span><br/>"

    # 특정 모습으로 바꾸기
    elif opcode == "lookLike:":
        costume_name = interpret_block(block[1])
        return f"<span class='{css_class}'>모습을 '{costume_name}'(으)로 바꾸기</span><br/>"

    elif opcode == "nextCostume":
        return f"<span class='{css_class}'>다음 모양으로 바꾸기</span><br/>"

    elif opcode == "costumeIndex":
        return f"<span class='{css_class}'>모양 #</span>"

    elif opcode == "think:duration:elapsed:from:":
        sentence = interpret_block(block[1])
        duration = interpret_block(block[2])

        sentence_disp = highlight_if_constant(sentence, block[1])
        duration_disp = highlight_if_constant(duration, block[2])

        return f"<span class='{css_class}'>{sentence_disp} 을(를) {duration_disp}초동안 생각하기</span><br/>"

    elif opcode == "think:":
        sentence = interpret_block(block[1])

        sentence_disp = highlight_if_constant(sentence, block[1])
        print(f"sentence_disp: {sentence_disp}")
        return f"<span class='{css_class}'>{sentence_disp} 생각하기</span><br/>"

    elif opcode == "say:duration:elapsed:from:":
        sentence = interpret_block(block[1])
        duration = interpret_block(block[2])

        sentence_disp = highlight_if_constant(sentence, block[1])
        duration_disp = highlight_if_constant(duration, block[2])

        return f"<span class='{css_class}'>{sentence_disp} 을(를) {duration_disp}초동안 말하기</span><br/>"

    elif opcode == "say:":
        sentence = interpret_block(block[1])

        sentence_disp = highlight_if_constant(sentence, block[1])

        return f"<span class='{css_class}'>{sentence_disp} 말하기</span><br/>"

    elif opcode == "show":
        return f"<span class='{css_class}'>보이기</span><br/>"
    elif opcode == "hide":
        return f"<span class='{css_class}'>숨기기</span><br/>"
    elif opcode == "scale":
        return f"<span class='{css_class}'>크기</span><br/>"
    elif opcode == "comrToFront":
        return f"<span class='{css_class}'>맨 앞으로 순서 바꾸기</span><br/>"
    elif opcode == "startScene":
        stage_name = interpret_block(block[1])
        return f"<span class='{css_class}'>배경을 {stage_name} (으)로 바꾸기</span><br/>"
    
    ############################

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
                    f"{'  ' * depth}</div><br/>"
                )
            else:
                return f"{'  ' * depth}<span class='cmd-control'>무한 반복하기 (내부 블록 없음)</span>"
        else:
            return f"{'  ' * depth}<span class='cmd-control'>무한 반복하기 (코드 없음)</span>"

    elif opcode == "doRepeat":
        if args and len(args) >= 2 and args[1]:
            repeat_count_raw = args[0]
            repeat_count = interpret_block(args[0])  # 반복 횟수
            repeat_count_disp = highlight_if_constant(repeat_count, repeat_count_raw)

            inner_blocks = args[1]  # 반복 내용
            inner_texts = [interpret_block(b) or "" for b in inner_blocks]

            # inner_text = "\n ".join(inner_texts)
            inner_text = "\n".join("  " * (depth + 1) + t for t in inner_texts)

            return (
                f"{'  ' * depth}<div class='block-wrapper cmd-control'>\n"
                f"{'  ' * (depth + 1)}<div class='block-header'>{repeat_count_disp}번 반복하기</div>\n"
                f"{'  ' * (depth + 1)}<div class='block-body'>\n"
                f"{inner_text}\n"
                f"{'  ' * (depth + 1)}</div>\n"
                f"{'  ' * depth}</div><br/>"
            )

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
                f"{'  ' * (depth + 1)}<div class='block-header'>{condition} 될 때까지 반복하기\n</div>\n"
                f"{'  ' * (depth + 1)}<div class='block-body'>\n"
                f"{inner_text}\n"
                f"{'  ' * (depth + 1)}</div>\n"
                f"{'  ' * depth}</div><br/>"
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
                f"{'  ' * depth}</div><br/>"
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

            return (
                f"{'  ' * depth}<div class='block-wrapper cmd-control'>\n"
                f"{'  ' * (depth + 1)}<div class='block-header'>만약 {condition} 라면</div>\n"
                # f"{'  ' * depth}만약 {condition} 라면:\n{if_part}\n{'  ' * depth}아니면:\n{else_part}"
                f"{'  ' * (depth + 1)}<div class='block-body'>\n"
                f"{if_part}\n"
                f"{'  ' * (depth + 1)}</div>\n"
                f"{'  ' * (depth + 1)}<div class='block-header'>아니면</div>\n"
                f"{'  ' * (depth + 1)}<div class='block-body'>\n"
                f"{else_part}\n"
                f"{'  ' * (depth + 1)}</div>\n"
                f"{'  ' * depth}</div><br/>"
            )
        else:
            return f"{'  ' * depth}조건문 (if-else) (코드 없음)"

    elif opcode == "waitUntil":
        if args:
            condition = interpret_block(args[0])
            return f"{condition}이(가) 참이 될 때까지 기다리기"
        else:
            return "조건 없음: 기다리기"

    elif opcode == "createCloneOf":
        target = interpret_block(block[1])
        target = "나 자신" if target == "_myself_" else target
        return f"<span class='{css_class}'>{target} 복제하기<span><br/>"

    elif opcode == "deleteClone":
        return f"<span class='{css_class}'>이 복제본 삭제하기<span><br/>"

    # 논리 연산: AND
    elif opcode == "&":
        left_raw = block[1]
        right_raw = block[2]

        left = interpret_block(block[1])
        right = interpret_block(block[2])
        left, right = isCorrectOperand(left, right)

        left_disp = highlight_if_constant(left, left_raw)
        right_disp = highlight_if_constant(right, right_raw)

        return f"<span class='{css_class}'>{left_disp} 그리고 {right_disp}</span>"

    elif opcode == "|":  # 또는?
        left_raw = block[1]
        right_raw = block[2]

        left = interpret_block(block[1])
        right = interpret_block(block[2])
        left, right = isCorrectOperand(left, right)

        left_disp = highlight_if_constant(left, left_raw)
        right_disp = highlight_if_constant(right, right_raw)

        return f"<span class='{css_class}'>{left_disp} 또는 {right_disp}</span>"

    # 비교 연산: 같다
    elif opcode == "=":

        left_raw = block[1]
        right_raw = block[2]

        left = interpret_block(block[1], depth)
        right = interpret_block(block[2], depth)
        left, right = isCorrectOperand(left, right)

        left_disp = highlight_if_constant(left, left_raw)
        right_disp = highlight_if_constant(right, right_raw)
        return f"<span class='{css_class}'>{left_disp} = {right_disp}</span>"

    # 문자열 길이
    elif opcode == "stringLength:":
        target_raw = block[1]
        target = interpret_block(block[1])
        target_disp = highlight_if_constant(target, target_raw)

        return f"<span class='{css_class}'>{target_disp}의 길이</span>"

    elif opcode == "letter:of:":
        idx = interpret_block(block[1])
        sentence = interpret_block(block[2])
        idx_disp = highlight_if_constant(idx, block[1])
        sentence_disp = highlight_if_constant(sentence, block[2])

        return (
            f"<span class='{css_class}'>{idx_disp}번째 글자 ( {sentence_disp} )</span>"
        )

    elif opcode == "concatenate:with:":
        str1 = interpret_block(block[1])
        str2 = interpret_block(block[2])

        str1_disp = highlight_if_constant(str1, block[1])
        str2_disp = highlight_if_constant(str2, block[2])

        return f"<span class='{css_class}'>{str1_disp} 와 {str2_disp} 결합하기</span>"

    elif opcode == "rounded":
        value = interpret_block(block[1])
        value_disp = highlight_if_constant(value, block[1])
        return f"<span class='{css_class}'>{value_disp} 반올림</span>"

    elif opcode == "computeFunction:of:":
        oper = interpret_block(block[1])
        value = interpret_block(block[2])
        oper = (
            "제곱근"
            if oper == "sqrt"
            else (
                "바닥 함수"
                if oper == "floor"
                else (
                    "천장 함수"
                    if oper == "ceil"
                    else "절대값" if oper == "abs" else oper
                )
            )
        )
        value_disp = highlight_if_constant(value, block[2])
        return f"<span class='{css_class}'>{oper} ({value_disp})</span>"

    # 비교 연산: 크다
    elif opcode == ">":
        left_raw = block[1]
        right_raw = block[2]

        left = interpret_block(block[1], depth)
        right = interpret_block(block[2], depth)
        left, right = isCorrectOperand(left, right)

        left_disp = highlight_if_constant(left, left_raw)
        right_disp = highlight_if_constant(right, right_raw)

        return f"<span class='{css_class}'>{left_disp} > {right_disp}</span>"

    # 비교 연산: 작다
    elif opcode == "<":
        left_raw = block[1]
        right_raw = block[2]

        left = interpret_block(block[1], depth)
        right = interpret_block(block[2], depth)
        left, right = isCorrectOperand(left, right)

        left_disp = highlight_if_constant(left, left_raw)
        right_disp = highlight_if_constant(right, right_raw)

        print(f"left:_{left}__{type(left)}\n")
        print(f"left_raw:_{left_raw}__{type(left_raw)}\n")
        print(f"left_disp:_{left_disp}")
        return f"<span class='{css_class}'>{left_disp} < {right_disp}</span>"

    # 리스트
    elif opcode == "showList:":
        lst = block[1]
        return f"<span class='{css_class}'>{lst} 리스트 보이기</span><br/>"

    elif opcode == "hideList:":
        lst = block[1]
        return f"<span class='{css_class}'>{lst} 리스트 숨기기</span><br/>"

    # 리스트에 값 추가
    elif opcode == "append:toList:":
        item = interpret_block(block[1])
        item_disp = highlight_if_constant(item, block[1])
        lst = interpret_block(block[2])
        return f"<span class='{css_class}'>{item_disp} 항목을 {lst} 에 추가하기</span><br/>"

    # 리스트 삽입
    elif opcode == "insert:at:ofList:":
        item = interpret_block(block[1])
        item_disp = highlight_if_constant(item, block[1])

        option = interpret_block(block[2])
        option_disp = highlight_if_constant(option, block[2])
        option_disp = (
            "마지막"
            if option_disp == "last"
            else "랜덤" if option_disp == "random" else option_disp
        )
        lst = interpret_block(block[3])
        return f"<span class='{css_class}'>{item_disp} 을(를) {option_disp} 번째 {lst} 에 넣기</span><br/>"

    # 리스트 변경
    elif opcode == "setLine:ofList:to:":
        option = interpret_block(block[1])
        option_disp = highlight_if_constant(option, block[1])
        option_disp = (
            "마지막"
            if option_disp == "last"
            else "랜덤" if option_disp == "random" else option_disp
        )

        lst = interpret_block(block[2])

        item = interpret_block(block[3])
        item_disp = highlight_if_constant(item, block[3])

        return f"<span class='{css_class}'>{option_disp} 번째 {lst} 의 항목을 {item_disp} (으)로 바꾸기</span><br/>"

    # 리스트 지우기
    elif opcode == "deleteLine:ofList:":
        option = interpret_block(block[1])
        option_disp = highlight_if_constant(option, block[1])
        option_disp = (
            "마지막"
            if option_disp == "last"
            else "모두" if option_disp == "all" else option_disp
        )
        lst = interpret_block(block[2])
        return f"<span class='{css_class}'>{option_disp} 번째 항목을 {lst} 에서 삭제하기</span><br/>"

    # 리스트 줄 수 세기
    elif opcode == "lineCountOfList:":
        lst = interpret_block(block[1])
        return f"<span class='{css_class}'>{lst} 리스트의 항목 수</span>"

    # 리스트 포함 여부
    elif opcode == "list:contains:":
        lst = interpret_block(block[1])
        item = interpret_block(block[2])
        item_disp = highlight_if_constant(item, block[2])
        return (
            f"<span class='{css_class}'>{lst} 리스트에 {item_disp} 포함되었는가?</span>"
        )

    elif opcode == "getLine:ofList:":
        item = interpret_block(block[1])
        item_disp = highlight_if_constant(item, block[1])
        lst= interpret_block(block[2]) 

        return (
            f"<span class='{css_class}'>{lst} 리스트의 {item}번째 항목</span>"
        )


    # 사용자 입력값 또는 파라미터 획득
    # ['getParam', 'Num', 'r']
    elif opcode == "getParam":
        param_name = interpret_block(block[1])
        return f"<span class='{css_class}'>{param_name}</span>"

    # 추가 블럭 정의
    elif opcode == "call":
        parameters = list(block[1].split())
        name = parameters[0]

        if len(parameters) == 1:
            return f"<span class='{css_class}'>{name}</span><br/>"

        tmp = ""
        for i in range(2, len(block)):
            t = interpret_block(block[i])
            t_disp = highlight_if_constant(t, block[1])
            tmp += t_disp

        return f"<span class='{css_class}'>{name} {tmp}</span><br/>"

        # tmp = ""
        # for i in range(1, len(parameters)):
        #     print(f"parameters: {parameters[i]}")
        #     if parameters[i] == "%s" or parameters[i] == "%n" or parameters[i] == "%b":
        #         t = interpret_block(parameters[i])
        #         t_disp = highlight_if_color(t, parameters[i])
        #         tmp += t_disp

        #     else:
        #         tmp += parameters[i]

        #     tmp += " "

    # 논리 연산: NOT
    elif opcode == "not":
        operand = interpret_block(block[1])
        return f"<span class='{css_class}'>{operand}이(가) 아니다</span>"

    # 산술 연산: 나머지 (%)
    elif opcode == "%":
        left = interpret_block(block[1])
        right = interpret_block(block[2])

        left_disp = highlight_if_constant(left, block[1])
        right_disp = highlight_if_constant(right, block[2])

        return (
            f"<span class='{css_class}'>{left_disp} 나누기 {right_disp}의 나머지</span>"
        )

    # 회전: 왼쪽으로 돌리기
    elif opcode == "turnLeft:":
        degrees_raw = block[1]
        degrees = interpret_block(block[1])
        degrees_disp = highlight_if_constant(degrees, degrees_raw)
        return f"<span class='{css_class}'>⟲ 왼쪽으로 {degrees_disp}도 회전</span><br/>"

    # 회전: 오른쪽으로 돌리기
    elif opcode == "turnRight:":

        degrees_raw = block[1]
        degrees = interpret_block(block[1])
        degrees_disp = highlight_if_constant(degrees, degrees_raw)
        return (
            f"<span class='{css_class}'>⟳ 오른쪽으로 {degrees_disp}도 회전</span><br/>"
        )

    # 이동: 앞으로 이동
    elif opcode == "forward:":
        steps_raw = block[1]
        steps = interpret_block(block[1])
        steps_disp = highlight_if_constant(steps, steps_raw)
        # return f"[({steps}) 만큼 움직이기]"
        return f"<span class='{css_class}'>{steps_disp} 만큼 움직이기</span><br/>"

        # return span(f"{steps} 만큼 움직이기", "cmd-motion")

    elif opcode == "gotoSpriteOrMouse:":
        destination = interpret_block(block[1])
        destination = (
            "마우스 포인터"
            if destination == "_mouse_"
            else "랜덤 위치" if destination == "_random_" else destination
        )
        return f"<span class='{css_class}'>{destination} 위치로 이동하기</span><br/>"

    # 형 변환 등 기본 처리
    else:
        # 리스트 내 모든 원소를 재귀 처리 후 문자열로 합치기
        if isinstance(block, list):
            return "[" + ", ".join(interpret_block(b) or "" for b in block) + "]<br/>"
        return f"{str(block)}<br/>"


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


# type: ignore
