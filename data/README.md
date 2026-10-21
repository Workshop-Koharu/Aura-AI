# AI Hub 데이터 합치기

## 지원 형식
- 하위 폴더를 끝까지 재귀 검색
- ZIP 내부 및 중첩 ZIP(최대 8단계)
- TXT, Markdown, JSON, JSONL, CSV, TSV, XML, HTML, DOCX, XLSX
- 구형 Word .doc는 자동 추출하지 않습니다. Word에서 .docx 또는 .txt로 변환하세요.
- PDF, 이미지, 오디오, 비디오 등은 이 스크립트에서 추출하지 않습니다.

## 실행
가상환경에서 아래 패키지를 설치합니다:
    pip install python-docx openpyxl

먼저 작은 테스트:
    python prepare_corpus.py --limit-files 5

전체 자료 처리:
    python prepare_corpus.py

결과:
- data/train.txt: 학습용 텍스트
- data/SOURCES.csv: 원본 경로, SHA-256, 포함/중복 상태

각 문서 앞에 다음 문구가 추가됩니다:
"본 AI데이터 등을 이용할 때에는 반드시 한국지능정보사회진흥원의 사업결과임을 밝혀야 하며, 본 AI데이터 등을 이용한 2차적 저작물에도 동일하게 밝혀야 합니다."

중요:
1. 데이터셋마다 개별 라이선스와 이용 조건이 다를 수 있습니다. 위 문구만으로 모든 조건을 충족한다고 보장할 수 없으므로 각 데이터셋의 약관도 확인하세요.
2. Validation/Test 폴더도 기본 포함됩니다. 공정한 평가를 위해 평가용 자료는 학습에서 분리하는 것이 좋습니다.
3. 대용량 ZIP은 오래 걸릴 수 있습니다. 암호화/손상 ZIP은 건너뛸 수 있습니다.
4. 학습 데이터는 매우 커질 수 있으므로 Git에 올리지 마세요.
