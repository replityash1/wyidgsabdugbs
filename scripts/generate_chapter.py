from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parents[1]

SETTINGS_FILE = ROOT / "config" / "settings.json"
PROMPT_FILE = ROOT / "prompts" / "writer.txt"


def gemini_generate(
    prompt: str,
    model: str,
    api_key: str,
) -> str:

    url = (
        "https://generativelanguage.googleapis.com/"
        f"v1beta/models/{model}:generateContent"
    )

    response = requests.post(
        url,
        headers={
            "x-goog-api-key": api_key,
            "Content-Type": "application/json",
        },
        json={
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {
                            "text": prompt
                        }
                    ],
                }
            ],
            "generationConfig": {
                "temperature": 0.2
            },
        },
        timeout=600,
    )

    response.raise_for_status()

    data = response.json()

    return (
        data["candidates"][0]
        ["content"]["parts"][0]
        ["text"]
    )


def main() -> None:

    if len(sys.argv) != 2:
        raise SystemExit(
            "Usage: generate_chapter.py TOPIC_ID"
        )

    topic_id = sys.argv[1]

    settings = json.loads(
        SETTINGS_FILE.read_text(
            encoding="utf-8"
        )
    )

    research_dir = (
        ROOT
        / "work"
        / "research"
        / topic_id
    )

    research = json.loads(
        (
            research_dir
            / "research.json"
        ).read_text(
            encoding="utf-8"
        )
    )

    sources = json.loads(
        (
            research_dir
            / "raw_sources.json"
        ).read_text(
            encoding="utf-8"
        )
    )

    writer_prompt = PROMPT_FILE.read_text(
        encoding="utf-8"
    )

    payload = json.dumps(
        {
            "research": research,
            "source_records": sources,
        },
        ensure_ascii=False,
        indent=2,
    )

    prompt = (
        writer_prompt
        + "\n\n"
        + "RESEARCH PACKAGE\n"
        + "================\n\n"
        + payload
    )

    api_key = os.environ.get(
        "GEMINI_API_KEY"
    )

    if not api_key:
        raise SystemExit(
            "GEMINI_API_KEY is missing."
        )

    for attempt in range(3):

        try:

            chapter = gemini_generate(
                prompt,
                settings["gemini_model"],
                api_key,
            )

            break

        except Exception as exc:

            print(
                f"Generation attempt "
                f"{attempt + 1} failed: {exc}"
            )

            if attempt == 2:
                raise

            time.sleep(
                5 * (attempt + 1)
            )

    output_dir = (
        ROOT
        / "work"
        / "chapters"
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    chapter_file = (
        output_dir
        / f"{topic_id}.md"
    )

    chapter_file.write_text(
        chapter,
        encoding="utf-8",
    )

    print(
        f"Chapter written: {chapter_file}"
    )


if __name__ == "__main__":
    main()
