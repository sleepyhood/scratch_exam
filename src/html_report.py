# html_report.py
import pandas as pd
import webbrowser
import os
from pathlib import Path
from bootstrap import jinja2
from jinja2 import Environment, FileSystemLoader
from datetime import datetime
import sys


def format_time(seconds):
    minutes = int(seconds) // 60
    secs = int(seconds) % 60
    return f"{minutes}분 {secs}초"


def save_results_as_html(results, meta_path=None, output_filename="채점결과.html"):

    import json

    # 🔍 meta.json에서 시간 정보 불러오기
    time_log = {}
    total_time = 0

    if meta_path and os.path.exists(meta_path):
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
            time_log = meta.get("time_log", {})
            total_time = meta.get("total_time", 0)

    # 각 결과 항목에 시간 정보 추가
    for i, r in enumerate(results):
        문제키 = f"문제{i+1}"
        sec = time_log.get(문제키, 0)
        r["풀이시간"] = format_time(sec)

    # 🔧 열기 버튼용 배치 파일 생성
    # generate_open_batch_files(results)

    # 템플릿 경로 설정 (PyInstaller 실행 대비)
    if getattr(sys, "frozen", False):
        # PyInstaller 실행 시 (_MEIPASS는 임시폴더)
        base_path = Path(sys._MEIPASS)
    else:
        # 일반 실행 시
        base_path = Path(__file__).parent

    template_dir = base_path / "templates"
    env = Environment(loader=FileSystemLoader(searchpath=template_dir))

    today = datetime.now().strftime("%Y-%m-%d")

    template = env.get_template("report_template.html")

    correct_count = sum(1 for r in results if r["정답여부"] == "O")
    rendered_html = template.render(
        results=results,
        correct_count=correct_count,
        today=today,
        total_time_str=format_time(total_time),  # ← 이 한 줄만 추가!
    )

    output_path = Path.home() / "Desktop" / output_filename
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(rendered_html)

    print(f"\n📄 채점 결과 리포트가 저장되었습니다: {output_path}")
    webbrowser.open(f"file://{output_path.resolve()}")
