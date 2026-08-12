from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

SYLLABUS = ROOT / "syllabus" / "ras_2026.json"
WORK = ROOT / "work"

TOPICS = WORK / "topics.json"
BATCHES = WORK / "batches.json"


def walk(
    subject: dict[str, Any],
    topic: dict[str, Any],
    parents: list[str],
    output: list[dict[str, Any]],
) -> None:

    children = topic.get(
        "children",
        [],
    ) or []

    path = parents + [
        topic["title_en"]
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
                "path": path,
            }
        )

    for child in children:
        walk(
            subject,
            child,
            path,
            output,
        )


def main() -> None:

    data = json.loads(
        SYLLABUS.read_text(
            encoding="utf-8"
        )
    )

    topics: list[dict[str, Any]] = []

    for subject in data["subjects"]:

        for topic in subject.get(
            "topics",
            [],
        ):

            walk(
                subject,
                topic,
                [],
                topics,
            )

    WORK.mkdir(
        parents=True,
        exist_ok=True,
    )

    TOPICS.write_text(
        json.dumps(
            topics,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    # ------------------------------------------------------------
    # BATCH TOPICS
    # ------------------------------------------------------------

    config = json.loads(
        (
            ROOT
            / "config"
            / "config.json"
        ).read_text(
            encoding="utf-8"
        )
    )

    per_runner = int(
        config["pipeline"]["topics_per_runner"]
    )

    batches = []

    for index in range(
        0,
        len(topics),
        per_runner,
    ):

        group = topics[
            index:index + per_runner
        ]

        batches.append(
            {
                "batch_id": (
                    index // per_runner
                ),
                "topic_ids": [
                    item["topic_id"]
                    for item in group
                ],
            }
        )

    BATCHES.write_text(
        json.dumps(
            batches,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(
        f"Topics: {len(topics)}"
    )

    print(
        f"Batches: {len(batches)}"
    )

    print(
        f"Topics per runner: {per_runner}"
    )


if __name__ == "__main__":
    main()
