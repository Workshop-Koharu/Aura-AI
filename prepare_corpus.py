from __future__ import annotations

import argparse
import atexit
import csv
import hashlib
import io
import json
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path, PurePosixPath

ATTRIBUTION = "본 AI데이터 등을 이용할 때에는 반드시 한국지능정보사회진흥원의 사업결과임을 밝혀야 하며, 본 AI데이터 등을 이용한 2차적 저작물에도 동일하게 밝혀야 합니다."
TEXT = {
    ".txt",
    ".md",
    ".text",
    ".json",
    ".jsonl",
    ".ndjson",
    ".csv",
    ".tsv",
    ".xml",
    ".html",
    ".htm",
}
SUPPORTED = TEXT | {".zip", ".doc", ".docx", ".xlsx"}
_WORD_APP = None
_DOC_CACHE: dict[str, str | None] = {}


def _close_word():
    global _WORD_APP
    if _WORD_APP is not None:
        try:
            _WORD_APP.Quit()
        except Exception:
            pass
        _WORD_APP = None


atexit.register(_close_word)


def decode(b):
    for enc in ("utf-8-sig", "cp949", "euc-kr", "utf-16"):
        try:
            return b.decode(enc)
        except UnicodeDecodeError:
            pass
    return b.decode("utf-8", errors="replace")


def flatten(v, key=""):
    if isinstance(v, dict):
        return "\n".join(s for k, x in v.items() if (s := flatten(x, f"{key}{k}")))
    if isinstance(v, list):
        return "\n".join(s for i, x in enumerate(v) if (s := flatten(x, f"{key}[{i}]")))
    if v is None or not str(v).strip():
        return ""
    return f"{key}: {v}" if key else str(v)


def convert(b, name):
    ext = PurePosixPath(name.replace("\\", "/")).suffix.lower()
    if ext in TEXT:
        raw = decode(b)
        if ext == ".json":
            try:
                return flatten(json.loads(raw))
            except json.JSONDecodeError:
                return raw
        if ext in {".jsonl", ".ndjson"}:
            out = []
            for line in raw.splitlines():
                if line.strip():
                    try:
                        out.append(flatten(json.loads(line)))
                    except json.JSONDecodeError:
                        out.append(line)
            return "\n".join(out)
        if ext in {".csv", ".tsv"}:
            try:
                return "\n".join(
                    " | ".join(c.strip() for c in row)
                    for row in csv.reader(
                        io.StringIO(raw), delimiter="\t" if ext == ".tsv" else ","
                    )
                    if any(c.strip() for c in row)
                )
            except csv.Error:
                return raw
        return raw
    if ext == ".docx":
        from docx import Document

        doc = Document(io.BytesIO(b))
        lines = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        for table in doc.tables:
            for row in table.rows:
                cells = [c.text.strip().replace("\n", " / ") for c in row.cells]
                if any(cells):
                    lines.append(" | ".join(cells))
        return "\n".join(lines)
    if ext == ".xlsx":
        from openpyxl import load_workbook

        book = load_workbook(io.BytesIO(b), read_only=True, data_only=True)
        lines = []
        try:
            for sheet in book.worksheets:
                lines.append(f"[시트: {sheet.title}]")
                for row in sheet.iter_rows(values_only=True):
                    vals = [str(v).strip() for v in row if v is not None and str(v).strip()]
                    if vals:
                        lines.append(" | ".join(vals))
        finally:
            book.close()
        return "\n".join(lines)
    return ""


def records(data, name, depth=0):
    ext = PurePosixPath(name.replace("\\", "/")).suffix.lower()
    if ext == ".zip" and data.startswith(b"PK"):
        if depth >= 8:
            print(f"[WARN] ZIP 중첩 8단계 제한: {name}", file=sys.stderr)
            return
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                for info in archive.infolist():
                    if info.is_dir():
                        continue
                    try:
                        # No arbitrary size cap: process every archive member. Huge archives may need lots of time/disk.
                        member = archive.read(info)
                        yield from records(member, f"{name}!/{info.filename}", depth + 1)
                    except Exception as exc:
                        print(
                            f"[ERROR] ZIP 내부 파일 읽기 실패 {name}!/{info.filename}: {exc}",
                            file=sys.stderr,
                        )
        except (zipfile.BadZipFile, OSError) as exc:
            print(f"[ERROR] ZIP 형식 오류 {name}: {exc}", file=sys.stderr)
        return
    if ext == ".zip" and not data.startswith(b"PK"):
        # Some datasets are incorrectly named .zip. Try decoding as text instead of silently skipping.
        text = decode(data).strip()
        if not text or "\ufffd" in text[:1000]:
            print(
                f"[ERROR] 확장자는 .zip이지만 ZIP 서명(PK)이 없고 텍스트로도 읽을 수 없음: {name}",
                file=sys.stderr,
            )
            return
    else:
        try:
            text = convert(data, name).strip()
        except ImportError as exc:
            print(
                f"[ERROR] {name}: DOCX/XLSX 지원 패키지 설치 필요: pip install python-docx openpyxl ({exc})",
                file=sys.stderr,
            )
            return
        except Exception as exc:
            print(f"[ERROR] 텍스트 추출 실패 {name}: {exc}", file=sys.stderr)
            return
    if ext == ".doc":
        # Reuse a single Microsoft Word process; starting LibreOffice for every one of
        # thousands of legacy documents adds hours of avoidable startup overhead.
        import os
        import tempfile

        doc_digest = hashlib.sha256(data).hexdigest()
        converted = False
        temp_name = None
        try:
            import win32com.client

            global _WORD_APP
            if _WORD_APP is None:
                _WORD_APP = win32com.client.DispatchEx("Word.Application")
                _WORD_APP.Visible = False
                _WORD_APP.DisplayAlerts = 0
                _WORD_APP.Options.ConfirmConversions = False
                _WORD_APP.Options.SaveNormalPrompt = False
            with tempfile.NamedTemporaryFile(suffix=".doc", delete=False) as tmp:
                tmp.write(data)
                temp_name = tmp.name
            document = _WORD_APP.Documents.Open(
                temp_name,
                ReadOnly=True,
                AddToRecentFiles=False,
                ConfirmConversions=False,
                OpenAndRepair=False,
            )
            try:
                text = document.Content.Text.strip()
                converted = bool(text)
            finally:
                document.Close(False)
        except Exception as word_exc:
            # Fallback is bounded so one damaged document cannot stall the full run.
            soffice = shutil.which("soffice") or r"C:\Program Files\LibreOffice\program\soffice.exe"
            try:
                if soffice and Path(soffice).is_file():
                    with tempfile.TemporaryDirectory(prefix="aura_doc_fallback_") as td:
                        tdpath = Path(td)
                        src = tdpath / "input.doc"
                        src.write_bytes(data)
                        result = subprocess.run(
                            [
                                soffice,
                                "--headless",
                                "--convert-to",
                                "txt:Text",
                                "--outdir",
                                str(tdpath),
                                str(src),
                            ],
                            capture_output=True,
                            text=True,
                            timeout=30,
                        )
                        txt = tdpath / "input.txt"
                        if result.returncode == 0 and txt.is_file():
                            text = decode(txt.read_bytes()).strip()
                            converted = bool(text)
            except Exception as lo_exc:
                print(
                    f"[ERROR] .doc conversion failed {name}: Word={word_exc}; LibreOffice={lo_exc}",
                    file=sys.stderr,
                )
        finally:
            if temp_name:
                try:
                    os.unlink(temp_name)
                except OSError:
                    pass
        _DOC_CACHE[doc_digest] = text if converted else None
        if not converted:
            print(f"[ERROR] legacy .doc extraction failed: {name}", file=sys.stderr)
            return
    if not text:
        return
    yield name, text, hashlib.sha256(data).hexdigest()


def main():
    p = argparse.ArgumentParser(
        description="Aura AI personal project: extract permitted datasets, log provenance, and keep source files safe."
    )
    p.add_argument("--source", type=Path, default=Path("data/source"))
    p.add_argument("--output", type=Path, default=Path("data/train.txt"))
    p.add_argument("--manifest", type=Path, default=Path("data/SOURCES.csv"))
    p.add_argument(
        "--web-manifest", type=Path, default=Path("../Aura-AI-Web/public/aihub-sources.json")
    )
    p.add_argument("--limit-files", type=int, default=0)
    p.add_argument("--delete-source-after-success", action="store_true", help=argparse.SUPPRESS)
    a = p.parse_args()
    root = a.source.resolve()
    if not root.is_dir():
        p.error(f"원본 폴더 없음: {root}")
    files = sorted(
        x
        for x in root.rglob("*")
        if x.is_file() and x.suffix.lower() in SUPPORTED and x.resolve() != a.output.resolve()
    )
    if a.limit_files:
        files = files[: a.limit_files]
    if not files:
        p.error(f"지원 파일 없음: {root}")
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.manifest.parent.mkdir(parents=True, exist_ok=True)
    seen = set()
    rows = []
    source_names = {}
    with a.output.open("w", encoding="utf-8", newline="\n") as out:
        out.write("AURA AI TRAINING CORPUS\n출처 표기: " + ATTRIBUTION + "\n\n")
        for i, path in enumerate(files, 1):
            rel = path.relative_to(root).as_posix()
            try:
                raw = path.read_bytes()
            except OSError as exc:
                print(f"[ERROR] 파일 읽기 실패 {rel}: {exc}", file=sys.stderr)
                continue
            for src, body, digest in records(raw, rel):
                size = len(body.encode("utf-8"))
                dataset = src.split("/")[0].split("!")[0]
                source_names.setdefault(
                    dataset, {"dataset": dataset, "path": dataset, "status": "처리됨"}
                )
                if digest in seen:
                    rows.append((src, digest, size, "duplicate content skipped"))
                    continue
                seen.add(digest)
                out.write(
                    f"\n\n========== DOCUMENT START ==========\n원본 경로: {src}\n출처 표기: {ATTRIBUTION}\n========== DOCUMENT CONTENT ==========\n{body}\n========== DOCUMENT END ==========\n"
                )
                rows.append((src, digest, size, "included"))
            if i % 100 == 0:
                print(f"처리 {i:,}/{len(files):,}개 파일")
    size = a.output.stat().st_size
    if size < 100:
        raise RuntimeError("결과 파일이 너무 작아 원본을 삭제하지 않습니다.")
    with a.manifest.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["source_path", "sha256", "extracted_utf8_bytes", "status"])
        w.writerows(rows)
    webdata = {
        "attribution": ATTRIBUTION,
        "sources": sorted(source_names.values(), key=lambda x: x["dataset"].casefold()),
        "manifest_file": "data/SOURCES.csv",
    }
    a.web_manifest.parent.mkdir(parents=True, exist_ok=True)
    a.web_manifest.write_text(
        json.dumps(webdata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    # Re-read generated artifacts before any optional deletion.
    if not a.output.is_file() or not a.manifest.is_file() or not a.web_manifest.is_file():
        raise RuntimeError("결과물 검증 실패: 원본 폴더는 삭제하지 않았습니다.")
    print(
        f"\n완료: 파일 {len(files):,}개 검색, 문서 {sum(1 for r in rows if r[3] == 'included'):,}개 포함"
    )
    print(f"train.txt: {a.output.resolve()} ({size:,} bytes / {size / 1024**3:.3f} GiB)")
    print(f"상세 출처: {a.manifest.resolve()}")
    print(f"웹앱 출처: {a.web_manifest.resolve()} ({len(source_names):,}개 데이터셋/상위 폴더)")
    print("출처 표기는 포함했지만 데이터셋별 이용 조건도 별도로 확인하세요.")
    if a.delete_source_after_success:
        raise RuntimeError(
            "안전 차단: 폴더 전체 삭제는 지원하지 않습니다. 모든 파일의 성공 여부와 출처를 개별 검증하는 정리 계획을 먼저 생성하세요. 원본은 삭제하지 않았습니다."
        )
    print("안전 모드: 원본은 삭제하지 않았습니다. 출처와 추출 결과를 검증한 뒤에만 정리하세요.")


if __name__ == "__main__":
    main()
