from __future__ import annotations
import argparse, csv, hashlib, io, json, sys, zipfile
from pathlib import Path, PurePosixPath

ATTRIBUTION = "본 AI데이터 등을 이용할 때에는 반드시 한국지능정보사회진흥원의 사업결과임을 밝혀야 하며, 본 AI데이터 등을 이용한 2차적 저작물에도 동일하게 밝혀야 합니다."
TEXT = {".txt", ".md", ".text", ".json", ".jsonl", ".ndjson", ".csv", ".tsv", ".xml", ".html", ".htm"}
SUPPORTED = TEXT | {".zip", ".docx", ".xlsx"}

def decode(data):
    for enc in ("utf-8-sig", "cp949", "euc-kr", "utf-16"):
        try: return data.decode(enc)
        except UnicodeDecodeError: pass
    return data.decode("utf-8", errors="replace")

def flatten(value, key=""):
    if isinstance(value, dict):
        return "\n".join(s for k, v in value.items() if (s := flatten(v, f"{key}{k}")))
    if isinstance(value, list):
        return "\n".join(s for i, v in enumerate(value) if (s := flatten(v, f"{key}[{i}]")))
    if value is None or not str(value).strip(): return ""
    return f"{key}: {value}" if key else str(value)

def convert(data, name):
    ext = PurePosixPath(name.replace("\\", "/")).suffix.lower()
    if ext in TEXT:
        raw = decode(data)
        if ext == ".json":
            try: return flatten(json.loads(raw))
            except json.JSONDecodeError: return raw
        if ext in {".jsonl", ".ndjson"}:
            lines = []
            for line in raw.splitlines():
                if line.strip():
                    try: lines.append(flatten(json.loads(line)))
                    except json.JSONDecodeError: lines.append(line)
            return "\n".join(lines)
        if ext in {".csv", ".tsv"}:
            try:
                rows = csv.reader(io.StringIO(raw), delimiter="\t" if ext == ".tsv" else ",")
                return "\n".join(" | ".join(c.strip() for c in row) for row in rows if any(c.strip() for c in row))
            except csv.Error: return raw
        return raw
    if ext == ".docx":
        from docx import Document
        doc = Document(io.BytesIO(data))
        lines = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        for table in doc.tables:
            for row in table.rows:
                cells = [c.text.strip().replace("\n", " / ") for c in row.cells]
                if any(cells): lines.append(" | ".join(cells))
        return "\n".join(lines)
    if ext == ".xlsx":
        from openpyxl import load_workbook
        book = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
        lines = []
        try:
            for sheet in book.worksheets:
                lines.append(f"[시트: {sheet.title}]")
                for row in sheet.iter_rows(values_only=True):
                    vals = [str(v).strip() for v in row if v is not None and str(v).strip()]
                    if vals: lines.append(" | ".join(vals))
        finally: book.close()
        return "\n".join(lines)
    return ""

def records(data, name, depth=0):
    if PurePosixPath(name.replace("\\", "/")).suffix.lower() == ".zip":
        if depth >= 8:
            print(f"[SKIP] ZIP 중첩 한도 초과: {name}", file=sys.stderr); return
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                for info in archive.infolist():
                    if info.is_dir(): continue
                    if info.file_size > 512 * 1024 * 1024:
                        print(f"[SKIP] ZIP 내부 파일 512MiB 초과: {name}!/{info.filename}", file=sys.stderr); continue
                    try: yield from records(archive.read(info), f"{name}!/{info.filename}", depth + 1)
                    except Exception as exc: print(f"[SKIP] {name}!/{info.filename}: {exc}", file=sys.stderr)
        except Exception as exc: print(f"[SKIP] ZIP 읽기 실패 {name}: {exc}", file=sys.stderr)
        return
    try: text = convert(data, name).strip()
    except ImportError as exc:
        print(f"[SKIP] {name}: 필요한 패키지를 설치하세요 (pip install python-docx openpyxl): {exc}", file=sys.stderr); return
    except Exception as exc: print(f"[SKIP] {name}: 텍스트 추출 실패: {exc}", file=sys.stderr); return
    if not text:
        if PurePosixPath(name).suffix.lower() == ".doc":
            print(f"[SKIP] 구형 .doc는 .docx 또는 .txt로 변환 필요: {name}", file=sys.stderr)
        return
    yield name, text, hashlib.sha256(data).hexdigest()

def main():
    parser = argparse.ArgumentParser(description="하위 폴더 및 중첩 ZIP의 AI Hub 텍스트 데이터를 합칩니다.")
    parser.add_argument("--source", type=Path, default=Path("data/source"))
    parser.add_argument("--output", type=Path, default=Path("data/train.txt"))
    parser.add_argument("--manifest", type=Path, default=Path("data/SOURCES.csv"))
    parser.add_argument("--limit-files", type=int, default=0, help="테스트용 파일 수 제한. 0은 전체")
    args = parser.parse_args()
    root = args.source.resolve()
    if not root.is_dir(): parser.error(f"원본 폴더가 없습니다: {root}")
    files = sorted(p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in SUPPORTED and p.resolve() != args.output.resolve())
    if args.limit_files > 0: files = files[:args.limit_files]
    if not files: parser.error(f"지원되는 파일을 찾지 못했습니다: {root}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    seen, rows, count = set(), [], 0
    with args.output.open("w", encoding="utf-8", newline="\n") as out:
        out.write("AURA AI TRAINING CORPUS\n출처 표기: " + ATTRIBUTION + "\n각 데이터셋의 개별 이용 조건도 확인해야 합니다.\n")
        for i, path in enumerate(files, 1):
            rel = path.relative_to(root).as_posix()
            try: raw = path.read_bytes()
            except OSError as exc:
                print(f"[SKIP] 파일 읽기 실패 {rel}: {exc}", file=sys.stderr); continue
            for source, text, digest in records(raw, rel):
                text_bytes = len(text.encode("utf-8"))
                if digest in seen:
                    rows.append((source, digest, text_bytes, "duplicate content skipped")); continue
                seen.add(digest)
                out.write(f"\n\n========== DOCUMENT START ==========\n원본 경로: {source}\n출처 표기: {ATTRIBUTION}\n========== DOCUMENT CONTENT ==========\n{text}\n========== DOCUMENT END ==========\n")
                rows.append((source, digest, text_bytes, "included")); count += 1
            if i % 100 == 0: print(f"검색 {i:,}/{len(files):,}개 파일, 추출 {count:,}개 문서")
    with args.manifest.open("w", encoding="utf-8-sig", newline="") as manifest:
        writer = csv.writer(manifest)
        writer.writerow(["source_path", "sha256", "extracted_utf8_bytes", "status"])
        writer.writerows(rows)
    size = args.output.stat().st_size
    print(f"\n완료: 검색 {len(files):,}개 파일, 추출 {count:,}개 문서")
    print(f"학습 파일: {args.output.resolve()} ({size:,} bytes / {size / 1024**3:.3f} GiB)")
    print(f"출처 목록: {args.manifest.resolve()}")
    print("NIA 출처 문구를 파일 머리말과 각 문서 앞에 추가했습니다.")
    print("주의: 출처 표기와 별개로 각 데이터셋의 개별 이용 조건을 확인하세요.")
    print("주의: Validation/Test 자료도 포함됩니다. 평가 시에는 학습 자료와 분리하세요.")

if __name__ == "__main__":
    main()
