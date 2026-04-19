# ayuso_audiobook

I really wanted to listen to David Fernández's book *"Ayuso: Zancadillas, Intrigas y Venganzas en la Corte de Madrid"* as an audiobook, but no official version existed. So I thought: why not build one myself? A bit of Python, a sprinkle of OpenAI TTS, and here we are — a fully automated pipeline that turns the PDF into a chapter-by-chapter Spanish audiobook. Problem solved. 🎧

## What it does

1. **Extracts** chapter text from the original PDF (`extractor.py`)
2. **Generates** one MP3 audiobook track per chapter using OpenAI's text-to-speech API (`generator.py`)
3. **Orchestrates** both steps with a single command (`ayuso_audiobook.py`)

## Requirements

- Python 3.10+
- An [OpenAI API key](https://platform.openai.com/api-keys) with access to the TTS API

```bash
pip install pypdf openai python-dotenv
```

## Setup

1. Clone the repo and place your PDF inside `original/`:

```
original/
└── Ayuso_prensa.pdf
```

2. Create a `.env` file in the project root:

```
OPENAI_API_KEY=your_api_key_here
```

## Usage

Run the full pipeline with defaults:

```bash
python ayuso_audiobook.py
```

Or customise it:

```bash
# Use a specific PDF
python ayuso_audiobook.py --pdf original/Ayuso_prensa.pdf

# Change the TTS voice
python ayuso_audiobook.py --voice nova

# Overwrite previously generated MP3s
python ayuso_audiobook.py --overwrite

# Run steps individually
python extractor.py --pdf original/Ayuso_prensa.pdf --output chapters_txt
python generator.py --input chapters_txt --output audiobook_mp3 --voice onyx
```

## Project structure

```
.
├── ayuso_audiobook.py   # Orchestrator — runs extract + generate
├── extractor.py         # PDF → chapter TXT files
├── generator.py         # TXT files → MP3 audiobook tracks
├── original/            # Place your source PDF here
├── chapters_txt/        # (generated) Extracted chapter text
├── audiobook_mp3/       # (generated) Final audiobook MP3s
└── .env                 # Your OpenAI API key (not committed)
```
