# html_report.py
import pandas as pd
import webbrowser
import os
from pathlib import Path
from bootstrap import jinja2
from jinja2 import Environment, FileSystemLoader
from datetime import datetime
import sys
def get_next_regrade_count(output_dir):
    output_dir = Path(output_dir)
    existing = list(output_dir.glob("재채점_*회차_채점결과.html"))
    return len(existing) + 1

def format_time(seconds):
    minutes = int(seconds) // 60
    secs = int(seconds) % 60
    return f"{minutes}분 {secs}초"

#def save_results_as_html(results, meta_path=None, output_filename=None, regrade_mode=False):
def save_results_as_html(results, meta_path=None, regrade_mode=False, output_filename=None):
    import json

    # 시간 로그
    time_log = {}
    total_time = 0
    username = "unknown"
    exam_round_name = "시험"
    date_str = datetime.now().strftime("%Y%m%d")

    if meta_path and os.path.exists(meta_path):
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
            time_log = meta.get("time_log", {})
            total_time = meta.get("total_time", 0)
            username = meta.get("username", "unknown")
            exam_round_name = meta.get("exam_round_name", "시험")
            date_str = meta.get("date", date_str)

    for i, r in enumerate(results):
        문제키 = f"문제{i+1}"
        sec = time_log.get(문제키, 0)
        r["풀이시간"] = format_time(sec)

    # 템플릿 로드
    if getattr(sys, "frozen", False):
        base_path = Path(sys._MEIPASS)
    else:
        base_path = Path(__file__).parent

    template_dir = base_path / "templates"
    env = Environment(loader=FileSystemLoader(searchpath=template_dir))
    template = env.get_template("report_template.html")

    correct_count = sum(1 for r in results if r["정답여부"] == "O")
    today = datetime.now().strftime("%Y-%m-%d")
    desktop = Path.home() / "Desktop"

    # 🔁 파일명 구성
    safe_exam_name = exam_round_name.replace(" ", "_").replace(".", "").replace(":", "")
    if regrade_mode:
        regrade_count = get_next_regrade_count(desktop)
        filename = f"{date_str}_{username}_{safe_exam_name}_재채점_{regrade_count}회차_채점결과.html"
    else:
        filename = f"{date_str}_{username}_{safe_exam_name}_채점결과.html"
        regrade_count = None

    output_path = desktop / filename
    print(f"output_path: {output_path}")
    html = template.render(
        results=results,
        correct_count=correct_count,
        today=today,
        total_time_str=format_time(total_time),
        regrade_count=regrade_count,
        
    )

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"📄 HTML 저장 완료: {output_path}")
    webbrowser.open(f"file://{output_path.resolve()}")



# def save_results_as_html(results, meta_path=None, output_filename="채점결과.html", output_dir=None, regrade_count=None):

#     import json

#     # 🔍 meta.json에서 시간 정보 불러오기
#     time_log = {}
#     total_time = 0

#     if meta_path and os.path.exists(meta_path):
#         with open(meta_path, "r", encoding="utf-8") as f:
#             meta = json.load(f)
#             time_log = meta.get("time_log", {})
#             total_time = meta.get("total_time", 0)

#     # 각 결과 항목에 시간 정보 추가
#     for i, r in enumerate(results):
#         문제키 = f"문제{i+1}"
#         sec = time_log.get(문제키, 0)
#         r["풀이시간"] = format_time(sec)

#     # 🔧 열기 버튼용 배치 파일 생성
#     # generate_open_batch_files(results)

#     # 템플릿 경로 설정 (PyInstaller 실행 대비)
#     if getattr(sys, "frozen", False):
#         # PyInstaller 실행 시 (_MEIPASS는 임시폴더)
#         base_path = Path(sys._MEIPASS)
#     else:
#         # 일반 실행 시
#         base_path = Path(__file__).parent

#     template_dir = base_path / "templates"
#     env = Environment(loader=FileSystemLoader(searchpath=template_dir))

#     today = datetime.now().strftime("%Y-%m-%d")

#     template = env.get_template("report_template.html")

#     correct_count = sum(1 for r in results if r["정답여부"] == "O")
#     rendered_html = template.render(
#         results=results,
#         correct_count=correct_count,
#         today=today,
#         total_time_str=format_time(total_time),  # ← 이 한 줄만 추가!
#                 regrade_count=regrade_count,  # ← 템플릿에서 사용 가능하게 넘겨줌

#     )

#     if output_dir is None:
#         output_path = Path.home() / "Desktop" / output_filename
#     else:
#         output_path = Path(output_dir) / output_filename

#     if regrade_count is not None:
#         regrade_count = get_next_regrade_count(output_dir)
#         output_filename = f"재채점_{regrade_count}회차_채점결과.html"
    
#     #output_path = Path.home() / "Desktop" / output_filename
#     with open(output_path, "w", encoding="utf-8") as f:
#         f.write(rendered_html)

#     print(f"\n📄 채점 결과 리포트가 저장되었습니다: {output_path}")
#     webbrowser.open(f"file://{output_path.resolve()}")
