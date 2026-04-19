#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
extractor.py

Purpose:
- Extract the full text from a Spanish PDF book.
- Detect chapter headings.
- Write one .txt file per chapter into an output directory.

Expected project layout:
    .
    ├── original/
    │   └── Ayuso_prensa.pdf
    ├── extractor.py
    ├── generator.py
    └── ayuso_audiobook.py

Usage:
    python extractor.py
    python extractor.py --pdf original/Ayuso_prensa.pdf
    python extractor.py --output chapters_txt

Requirements:
    pip install pypdf
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import List, Tuple

from pypdf import PdfReader


DEFAULT_INPUT_DIR = Path("original")
DEFAULT_OUTPUT_DIR = Path("chapters_txt")


def find_default_pdf(input_dir: Path) -> Path:
    if not input_dir.exists() or not input_dir.is_dir():
        raise FileNotFoundError(f"Input directory not found: {input_dir}")

    pdf_files = sorted(input_dir.glob("*.pdf"))
    if not pdf_files:
        raise FileNotFoundError(f"No PDF files found in: {input_dir}")

    return pdf_files[0]


def extract_pdf_text(pdf_path: Path) -> str:
    reader = PdfReader(str(pdf_path))
    pages = []

    for page_number, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception as exc:
            print(
                f"[WARNING] Could not extract text from page {page_number}: {exc}",
                file=sys.stderr,
            )
            text = ""
        pages.append(text)

    return "\n\n".join(pages)


def clean_text(text: str) -> str:
    repeated_noise = [
        "copia de prensa",
        "Libros del K.O. Todos los derechos reservados",
    ]

    for noise in repeated_noise:
        text = re.sub(rf"\b{re.escape(noise)}\b", "", text, flags=re.IGNORECASE)

    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Fix words split by a hyphen at line breaks.
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)

    # Remove page numbers standing alone or as simple pairs.
    text = re.sub(r"(?m)^\s*\d+\s*$", "", text)
    text = re.sub(r"(?m)^\s*\d+\s+\d+\s*$", "", text)

    # Normalize spaces and blank lines.
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def build_heading_patterns() -> List[re.Pattern[str]]:
    return [
        re.compile(
            r"(?m)^(?P<title>\d{1,2}\.\s+[A-ZÁÉÍÓÚÜÑ0-9 ,«»\"'():;!\-]+)\s*$"
        ),
        re.compile(
            r"(?m)^(?P<title>ANEXO\s+\d+\.\s+[A-ZÁÉÍÓÚÜÑ0-9 ,«»\"'():;!\-]+)\s*$"
        ),
    ]


def detect_chapters(text: str) -> List[Tuple[str, int, int]]:
    matches = []

    for pattern in build_heading_patterns():
        matches.extend(pattern.finditer(text))

    matches = sorted(matches, key=lambda m: m.start())

    if not matches:
        return []

    raw_sections: List[Tuple[str, int, int]] = []
    for index, match in enumerate(matches):
        title = match.group("title").strip()
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        raw_sections.append((title, start, end))

    # Filter out short index/table-of-contents matches.
    filtered_sections: List[Tuple[str, int, int]] = []
    for title, start, end in raw_sections:
        block = text[start:end].strip()
        if len(block) >= 2000:
            filtered_sections.append((title, start, end))

    return filtered_sections


def slugify(title: str) -> str:
    normalized = title.lower()

    replacements = {
        "á": "a",
        "é": "e",
        "í": "i",
        "ó": "o",
        "ú": "u",
        "ü": "u",
        "ñ": "n",
        "«": "",
        "»": "",
        '"': "",
        "'": "",
    }

    for source, target in replacements.items():
        normalized = normalized.replace(source, target)

    normalized = re.sub(r"[^a-z0-9._ -]+", "", normalized)
    normalized = normalized.replace(" ", "_")
    normalized = re.sub(r"_+", "_", normalized).strip("._-")

    return normalized


def write_chapters(
    text: str,
    chapters: List[Tuple[str, int, int]],
    output_dir: Path,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    for title, start, end in chapters:
        content = text[start:end].strip()

        content = re.sub(
            rf"^(?:{re.escape(title)}\s*)+",
            f"{title}\n\n",
            content,
            flags=re.IGNORECASE,
        )

        filename = slugify(title) + ".txt"
        file_path = output_dir / filename
        file_path.write_text(content, encoding="utf-8")
        print(f"[OK] Created: {file_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract one TXT file per chapter from a Spanish PDF book."
    )
    parser.add_argument(
        "--pdf",
        type=Path,
        default=None,
        help="Path to the input PDF. If omitted, the first PDF inside ./original is used.",
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=DEFAULT_INPUT_DIR,
        help="Directory containing the original PDF when --pdf is not provided.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory where chapter TXT files will be created.",
    )
    args = parser.parse_args()

    pdf_path = args.pdf if args.pdf else find_default_pdf(args.input_dir)

    if not pdf_path.exists():
        print(f"[ERROR] PDF not found: {pdf_path}", file=sys.stderr)
        sys.exit(1)

    print(f"[INFO] Input PDF: {pdf_path}")
    print("[1/4] Extracting text from PDF...")
    text = extract_pdf_text(pdf_path)

    print("[2/4] Cleaning extracted text...")
    text = clean_text(text)

    print("[3/4] Detecting chapter boundaries...")
    chapters = detect_chapters(text)

    if not chapters:
        print(
            "[ERROR] No chapter headings were detected automatically.",
            file=sys.stderr,
        )
        sys.exit(2)

    print(f"[INFO] Chapters detected: {len(chapters)}")

    print("[4/4] Writing chapter TXT files...")
    write_chapters(text, chapters, args.output)

    print(f"[DONE] Chapter files saved in: {args.output.resolve()}")


if __name__ == "__main__":
    main()
