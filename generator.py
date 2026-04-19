#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
generator.py

Purpose:
- Read all .txt files from a directory.
- Generate one MP3 per TXT file with the same base filename.
- Use OpenAI text-to-speech for Spanish audiobook narration.

Expected project layout:
    .
    ├── chapters_txt/
    │   ├── 1_pandillera_y_callejera.txt
    │   └── ...
    ├── generator.py
    └── .env

Requirements:
    pip install openai python-dotenv

Environment:
    OPENAI_API_KEY=your_api_key
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import List

from dotenv import load_dotenv
from openai import OpenAI


DEFAULT_MODEL = "gpt-4o-mini-tts"
DEFAULT_VOICE = "onyx"
DEFAULT_AUDIO_FORMAT = "mp3"
DEFAULT_INPUT_DIR = Path("chapters_txt")
DEFAULT_OUTPUT_DIR = Path("audiobook_mp3")

DEFAULT_INSTRUCTIONS = (
    "Read in European Spanish, with a classic male narration style, "
    "medium pace, clear diction, formal but natural tone, and restrained expression. "
    "Respect punctuation and paragraph pauses. "
    "This is a full reading of a Spanish non-fiction book."
)

MAX_CHARS_PER_CHUNK = 3500


def split_text_into_chunks(text: str, max_chars: int = MAX_CHARS_PER_CHUNK) -> List[str]:
    text = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    if len(text) <= max_chars:
        return [text]

    paragraphs = [paragraph.strip() for paragraph in text.split("\n\n") if paragraph.strip()]

    chunks: List[str] = []
    current_chunk = ""

    for paragraph in paragraphs:
        if not current_chunk:
            current_chunk = paragraph
            continue

        candidate = current_chunk + "\n\n" + paragraph
        if len(candidate) <= max_chars:
            current_chunk = candidate
        else:
            chunks.append(current_chunk)
            current_chunk = paragraph

    if current_chunk:
        chunks.append(current_chunk)

    final_chunks: List[str] = []
    for chunk in chunks:
        if len(chunk) <= max_chars:
            final_chunks.append(chunk)
            continue

        sentences = re.split(r"(?<=[\.\!\?\:;])\s+", chunk)
        current_chunk = ""

        for sentence in sentences:
            if not current_chunk:
                current_chunk = sentence
                continue

            candidate = current_chunk + " " + sentence
            if len(candidate) <= max_chars:
                current_chunk = candidate
            else:
                final_chunks.append(current_chunk)
                current_chunk = sentence

        if current_chunk:
            final_chunks.append(current_chunk)

    return [chunk.strip() for chunk in final_chunks if chunk.strip()]


def synthesize_chunk(
    client: OpenAI,
    text: str,
    output_path: Path,
    model: str,
    voice: str,
    instructions: str,
    audio_format: str = DEFAULT_AUDIO_FORMAT,
) -> None:
    with client.audio.speech.with_streaming_response.create(
        model=model,
        voice=voice,
        input=text,
        instructions=instructions,
        response_format=audio_format,
    ) as response:
        response.stream_to_file(output_path)


def concatenate_mp3_files(parts: List[Path], destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)

    with open(destination, "wb") as output_file:
        for part in parts:
            with open(part, "rb") as input_file:
                output_file.write(input_file.read())


def generate_audio_for_text_file(
    client: OpenAI,
    txt_path: Path,
    output_dir: Path,
    model: str,
    voice: str,
    instructions: str,
    overwrite: bool = False,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    mp3_path = output_dir / f"{txt_path.stem}.mp3"

    if mp3_path.exists() and not overwrite:
        print(f"[SKIP] Audio already exists: {mp3_path.name}")
        return

    text = txt_path.read_text(encoding="utf-8").strip()
    if not text:
        print(f"[SKIP] Empty file: {txt_path.name}")
        return

    chunks = split_text_into_chunks(text)
    print(f"[INFO] {txt_path.name}: {len(chunks)} chunk(s)")

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        part_files: List[Path] = []

        for index, chunk in enumerate(chunks, start=1):
            part_path = temp_path / f"{txt_path.stem}.part{index:03d}.mp3"
            print(f"       -> Generating chunk {index}/{len(chunks)}")
            synthesize_chunk(
                client=client,
                text=chunk,
                output_path=part_path,
                model=model,
                voice=voice,
                instructions=instructions,
                audio_format=DEFAULT_AUDIO_FORMAT,
            )
            part_files.append(part_path)

        print(f"       -> Merging chunks into {mp3_path.name}")
        concatenate_mp3_files(part_files, mp3_path)

    print(f"[OK] Generated: {mp3_path}")


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="Generate one MP3 audiobook track per TXT file."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT_DIR,
        help="Directory containing chapter TXT files.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory where MP3 files will be written.",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"TTS model name. Default: {DEFAULT_MODEL}",
    )
    parser.add_argument(
        "--voice",
        default=DEFAULT_VOICE,
        help=f"TTS voice name. Default: {DEFAULT_VOICE}",
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

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("[ERROR] OPENAI_API_KEY is not set.", file=sys.stderr)
        sys.exit(1)

    input_dir = args.input
    if not input_dir.exists() or not input_dir.is_dir():
        print(f"[ERROR] Invalid input directory: {input_dir}", file=sys.stderr)
        sys.exit(1)

    txt_files = sorted(input_dir.glob("*.txt"))
    if not txt_files:
        print(f"[ERROR] No TXT files found in: {input_dir.resolve()}", file=sys.stderr)
        sys.exit(1)

    client = OpenAI(api_key=api_key)

    print(f"[INFO] Input directory:  {input_dir.resolve()}")
    print(f"[INFO] Output directory: {args.output.resolve()}")
    print(f"[INFO] TXT files found:  {len(txt_files)}")
    print(f"[INFO] TTS model:        {args.model}")
    print(f"[INFO] TTS voice:        {args.voice}")

    for txt_file in txt_files:
        try:
            generate_audio_for_text_file(
                client=client,
                txt_path=txt_file,
                output_dir=args.output,
                model=args.model,
                voice=args.voice,
                instructions=args.instructions,
                overwrite=args.overwrite,
            )
        except Exception as exc:
            print(f"[ERROR] Failed for {txt_file.name}: {exc}", file=sys.stderr)

    print("[DONE] All available TXT files were processed.")


if __name__ == "__main__":
    main()
