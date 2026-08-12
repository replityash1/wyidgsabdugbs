from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

SYLLABUS_FILE = ROOT / "syllabus" / "ras_2026.json"
OUTPUT_FILE = ROOT / "work" / "topics.json"


def walk_topics(
    subject: dict[str, Any],
    topic: dict[str, Any],
    parent_titles: list[str],
    output: list[dict[str, Any]],
) -> None:

    children = topic.get("children", []) or []

    current_path = parent_titles + [
        topic.get("title_en", "")
    ]

    if not children:
        output.append(
            {
                "subject_id": subject["id"],
                "subject_title_hi": subject["title_hi"],
                "subject_title_en": subject["title_en"],
                "topic_id": topic["id"],
                "topic_title_hi": topic["title_hi"],
                "topic_title_en": topic["title_en"],
                "path_en": current_path,
            }
        )

    for child in children:
        walk_topics(
            subject,
            child,
            current_path,
            output,
        )


def main() -> None:
    data = json.loads(
        SYLLABUS_FILE.read_text(
            encoding="utf-8"
        )
    )

    topics: list[dict[str, Any]] = []

    for subject in data["subjects"]:
        for topic in subject.get("topics", []):
            walk_topics(
                subject,
                topic,
                [],
                topics,
            )

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUTPUT_FILE.write_text(
        json.dumps(
            topics,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(
        f"Generated {len(topics)} leaf topics."
    )


if __name__ == "__main__":
    main()
