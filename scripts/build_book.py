from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

TOPICS_FILE = ROOT / "work" / "topics.json"
CHAPTERS_DIR = ROOT / "work" / "chapters"
OUTPUT_DIR = ROOT / "output"


def main() -> None:

    topics = json.loads(
        TOPICS_FILE.read_text(
            encoding="utf-8"
        )
    )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    book_parts: list[str] = []

    book_parts.append(
        "# RAS Pre 2026\n\n"
        "# Complete Syllabus Knowledge Book\n\n"
        "> Evidence-first study material generated from "
        "the supplied RAS syllabus and researched source records.\n\n"
    )

    current_subject = None

    for topic in topics:

        subject = topic[
            "subject_title_en"
        ]

        if subject != current_subject:

            current_subject = subject

            book_parts.append(
                "\n---\n\n"
                f"# {topic['subject_title_hi']}\n"
                f"## {subject}\n\n"
            )

        chapter = (
            CHAPTERS_DIR
            / f"{topic['topic_id']}.md"
        )

        if not chapter.exists():
            book_parts.append(
                "\n> [MISSING CHAPTER]\n\n"
            )
            continue

        book_parts.append(
            chapter.read_text(
                encoding="utf-8"
            )
        )

        book_parts.append(
            "\n\n---\n\n"
        )

    # ------------------------------------------------------------
    # REFERENCES
    # ------------------------------------------------------------

    book_parts.append(
        "\n# Research Coverage\n\n"
    )

    all_sources: dict[str, dict] = {}

    for topic in topics:

        research_file = (
            ROOT
            / "work"
            / "research"
            / topic["topic_id"]
            / "research.json"
        )

        if not research_file.exists():
            continue

        data = json.loads(
            research_file.read_text(
                encoding="utf-8"
            )
        )

        for source in data.get(
            "sources",
            []
        ):

            key = source["source_id"]

            all_sources[
                f"{topic['topic_id']}::{key}"
            ] = source

    for key, source in all_sources.items():

        book_parts.append(
            f"- **{source.get('title', '')}** — "
            f"{source.get('url', '')}\n"
        )

    output = "".join(book_parts)

    book_file = (
        OUTPUT_DIR
        / "RAS_Pre_2026_Complete_Book.md"
    )

    book_file.write_text(
        output,
        encoding="utf-8",
    )

    print(
        f"Book created: {book_file}"
    )


if __name__ == "__main__":
    main()
