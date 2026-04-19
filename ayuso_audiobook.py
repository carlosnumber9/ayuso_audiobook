#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ayuso_audiobook.py

Purpose:
- Run the full audiobook pipeline with a single command.
- Step 1: extract chapter TXT files from the original PDF.
- Step 2: generate one MP3 audiobook track per TXT file.

Expected project layout:
    .
    ├── original/
    │   └── Ayuso_prensa.pdf
    ├── extractor.py
    ├── generator.py
    ├── ayuso_audiobook.py
    └── .env

Requirements:
    pip install pypdf openai python-dotenv

Environment:
    OPENAI_API_KEY=your_api_key

Usage:
    python ayuso_audiobook.py
    python ayuso_audiobook.py --pdf original/Ayuso_prensa.pdf
    python ayuso_audiobook.py --voice onyx
    python ayuso_audiobook.py --overwrite
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


DEFAULT_PDF_DIR = Path("original")
DEFAULT_TXT_DIR = Path("chapters_txt")
DEFAULT_MP3_DIR = Path("audiobook_mp3")
DEFAULT_VOICE = "onyx"
DEFAULT_MODEL = "gpt-4o-mini-tts"

DEFAULT_INSTRUCTIONS = (
    "Read in European Spanish, with a classic male narration style, "
    "medium pace, clear diction, formal but natural tone, and restrained expression. "
    "Respect punctuation and paragraph pauses. "
    "This is a full reading of a Spanish non-fiction book."
)


def find_default_pdf(pdf_dir: Path) -> Path:
    if not pdf_dir.exists() or not pdf_dir.is_dir():
        raise FileNotFoundError(f"PDF directory not found: {pdf_dir}")

    pdf_files = sorted(pdf_dir.glob("*.pdf"))
    if not pdf_files:
        raise FileNotFoundError(f"No PDF files found in: {pdf_dir}")

    return pdf_files[0]


def run_command(command: list[str]) -> None:
    print(f"[RUN] {' '.join(command)}")
    completed = subprocess.run(command)
    if completed.returncode != 0:
        raise RuntimeError(f"Command failed with exit code {completed.returncode}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create the full Spanish audiobook pipeline with one command."
    )
    parser.add_argument(
        "--pdf",
        type=Path,
        default=None,
        help="Path to the source PDF. If omitted, the first PDF in ./original is used.",
    )
    parser.add_argument(
        "--pdf-dir",
        type=Path,
        default=DEFAULT_PDF_DIR,
        help="Directory containing the original PDF when --pdf is not provided.",
    )
    parser.add_argument(
        "--txt-output",
        type=Path,
        default=DEFAULT_TXT_DIR,
        help="Directory where extracted chapter TXT files will be created.",
    )
    parser.add_argument(
        "--mp3-output",
        type=Path,
        default=DEFAULT_MP3_DIR,
        help="Directory where MP3 audiobook tracks will be created.",
    )
    parser.add_argument(
        "--voice",
        default=DEFAULT_VOICE,
        help=f"TTS voice to use. Default: {DEFAULT_VOICE}",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"TTS model to use. Default: {DEFAULT_MODEL}",
    )
    parser.add_argument(
        "--instructions",
        default=DEFAULT_INSTRUCTIONS,
        help="Voice instructions passed to the TTS model.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing MP3 files.",
    )
    args = parser.parse_args()

    try:
        pdf_path = args.pdf if args.pdf else find_default_pdf(args.pdf_dir)
    except Exception as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        sys.exit(1)

    extractor_script = Path(__file__).with_name("extractor.py")
    generator_script = Path(__file__).with_name("generator.py")

    if not extractor_script.exists():
        print(f"[ERROR] Missing script: {extractor_script}", file=sys.stderr)
        sys.exit(1)

    if not generator_script.exists():
        print(f"[ERROR] Missing script: {generator_script}", file=sys.stderr)
        sys.exit(1)

    extractor_command = [
        sys.executable,
        str(extractor_script),
        "--pdf",
        str(pdf_path),
        "--output",
        str(args.txt_output),
    ]

    generator_command = [
        sys.executable,
        str(generator_script),
        "--input",
        str(args.txt_output),
        "--output",
        str(args.mp3_output),
        "--model",
        args.model,
        "--voice",
        args.voice,
        "--instructions",
        args.instructions,
    ]

    if args.overwrite:
        generator_command.append("--overwrite")

    try:
        print("[STEP 1] Extracting chapter TXT files...")
        run_command(extractor_command)

        print("[STEP 2] Generating MP3 audiobook tracks...")
        run_command(generator_command)

    except Exception as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        sys.exit(1)

    print("[DONE] Audiobook pipeline completed successfully.")


if __name__ == "__main__":
    main()
