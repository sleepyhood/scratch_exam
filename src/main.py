from exam_selector import ExamSelector
from loading_json import load_config
from pathlib import Path
from html_report import save_results_as_html
import traceback

# 사용 예시
config = load_config()
#default_exam_folder = config["default_exam_folder"]
default_exam_folder = config["default_exam_folder_toDCT2"]

default_exam_folder = Path(default_exam_folder)
print(default_exam_folder)

if __name__ == "__main__":

    # base_path = r"자격증 준비"
    selector = ExamSelector(default_exam_folder)
    selector.mainloop()

    # # 💡 mainloop가 종료된 후 (즉, destroy 이후) 자동 채점 실행
    from grader import grade_from_meta, print_results

    # 제출본 내부 meta.json 경로
    meta_path = getattr(selector, "submission_meta_path", None)

    try:
        if meta_path.exists():
            results = grade_from_meta(meta_path)
            print_results(results)

            html_name = str(getattr(selector, "folder_name", None))
            html_name += ".html"
            # 💡 예쁜 HTML로 저장
            save_results_as_html(
                results, meta_path=meta_path, output_filename=html_name
            )
        else:
            print("❌ meta.json 파일이 존재하지 않습니다. 채점 생략.")
    except Exception as e:
        print("⚠️ 예외 발생:")
        traceback.print_exc()
