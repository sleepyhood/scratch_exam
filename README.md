# COS Scratch 자격증 자동 채점기

## 프로젝트 소개

본 프로젝트는 **Scratch 2.0 기반 COS 자격증 시험**의 `.sb2` 문제 파일을 자동으로 채점하고,  
채점 결과를 HTML 리포트로 출력하는 도구입니다.

- 제출된 문제 파일과 정답 파일을 비교하여 정답 여부를 판단합니다.
- 각 문제별 풀이 시간, 오류 내용 등 상세 정보를 제공합니다.
- Windows 환경에서 실행 가능하며, PyInstaller로 `.exe` 파일도 배포합니다.

---

## 주요 기능

- 시험 회차 선택 GUI
- PDF 문제지 자동 연동 및 열기 지원
- `.sb2` 문제 및 정답 파일 자동 비교 채점
- HTML 포맷의 채점 결과 리포트 생성 및 자동 열기
- 문제별 풀이 시간 기록 및 누적 지원

---

## 파일 및 폴더 구조

```

C:.
\| app_icon.ico
\| bootstrap.py
\| exam_app.py
\| exam_selector.py
\| grader.py
\| html_report.py
\| loading_json.py
\| main.py
\| main.spec
\| metadata.json
\| pdf_viewer.py
\| requirements.txt
|
+---build
\| ---main
\| ...
|
+---dist
\| config.json
\| main.exe
|
+---templates
\| report_template.html
|
\---**pycache**
...

```

---

## 설정 (config.json) <- 중요합니다. 폴더 루트를 지정해야만 올바르게 작동합니다.

```json
{
  "scratch_path": "C:/Program Files (x86)/Scratch 2/Scratch 2.exe",
  "default_exam_folder": "C:\\자격증 준비",
  "root_password": "1234"
}
```

- `scratch_path`: Scratch 2 실행 파일 경로
- `default_exam_folder`: 시험 파일이 저장된 최상위 폴더 경로
- `root_password`: 관리자 모드 진입 비밀번호

---

## 시험 폴더 구조 규칙

시험 폴더는 다음과 같은 계층 구조를 따라야 합니다:

```
default_exam_folder (예: 자격증 준비)
├─ COS 3급
│  ├─ 01. 3급 기출유형1
│  │  ├─ COS3_01_문제
│  │  └─ COS3_01_정답
│  ├─ 02. 3급 기출유형10 (정답 미완성)
│  │  ├─ COS3_02_문제
│  │  └─ COS3_02_정답
├─ COS 2급
│  ├─ ...
```

- 최상위는 급수명 폴더 (예: `COS 3급`, `COS 2급`)
- 그 안에 회차별 폴더
- 회차 폴더 내에 `문제` 폴더와 `정답` 폴더가 반드시 존재해야 인식됩니다.

---

## 실행 방법

1. Python 환경에서 실행

```bash
pip install -r requirements.txt
python main.py
```

2. 또는 dist 폴더 내 `main.exe` 실행 (Windows 전용)

---

## 라이선스

MIT License

---

## 문의 및 기여

- Pull Request 및 Issue는 언제든 환영합니다!

---

### 감사합니다!
