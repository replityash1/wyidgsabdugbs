from __future__ import annotations

import html
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

TOPICS = json.loads(
    (
        ROOT
        / "work"
        / "topics.json"
    ).read_text(
        encoding="utf-8"
    )
)

RESULTS = (
    ROOT
    / "work"
    / "results"
)

OUTPUT = ROOT / "output"

OUTPUT.mkdir(
    parents=True,
    exist_ok=True,
)


def main() -> None:

    markdown = []

    markdown.append(
        "# RAS Pre 2026\n\n"
        "# Complete Evidence-Based Knowledge Book\n\n"
    )

    markdown.append(
        "> Generated from the supplied RAS syllabus. "
        "Factual material is tied to retrieved source records.\n\n"
    )

    current_subject = None

    source_registry = {}

    for topic in TOPICS:

        topic_id = topic[
            "topic_id"
        ]

        result_dir = (
            RESULTS
            / topic_id
        )

        chapter_file = (
            result_dir
            / "chapter.md"
        )

        if not chapter_file.exists():
            continue

        if (
            topic["subject_id"]
            != current_subject
        ):

            current_subject = (
                topic["subject_id"]
            )

            markdown.append(
                "\n\n---\n\n"
                f"# {topic['subject_title_hi']}\n"
                f"## {topic['subject_title_en']}\n\n"
            )

        markdown.append(
            chapter_file.read_text(
                encoding="utf-8"
            )
        )

        markdown.append(
            "\n\n---\n\n"
        )

        source_file = (
            result_dir
            / "sources.json"
        )

        if source_file.exists():

            data = json.loads(
                source_file.read_text(
                    encoding="utf-8"
                )
            )

            for source in data.get(
                "sources",
                [],
            ):

                key = (
                    source["url"]
                )

                source_registry[
                    key
                ] = source

    # ------------------------------------------------------------
    # SOURCE REGISTER
    # ------------------------------------------------------------

    markdown.append(
        "\n# Source Register\n\n"
    )

    for index, source in enumerate(
        source_registry.values(),
        start=1,
    ):

        markdown.append(
            f"{index}. **"
            f"{source.get('title', '')}"
            f"** — "
            f"{source.get('url', '')}\n"
        )

    markdown_text = "".join(
        markdown
    )

    markdown_file = (
        OUTPUT
        / "RAS_Pre_2026_Book.md"
    )

    markdown_file.write_text(
        markdown_text,
        encoding="utf-8",
    )

    # ------------------------------------------------------------
    # SIMPLE HTML
    # ------------------------------------------------------------

    body_parts = []

    for block in markdown_text.split(
        "\n\n"
    ):

        escaped = html.escape(
            block
        )

        if escaped.startswith(
            "# "
        ):

            body_parts.append(
                "<h1>"
                + html.escape(
                    block[2:]
                )
                + "</h1>"
            )

        elif escaped.startswith(
            "## "
        ):

            body_parts.append(
                "<h2>"
                + html.escape(
                    block[3:]
                )
                + "</h2>"
            )

        elif escaped.startswith(
            "### "
        ):

            body_parts.append(
                "<h3>"
                + html.escape(
                    block[4:]
                )
                + "</h3>"
            )

        elif escaped.startswith(
            "> "
        ):

            body_parts.append(
                "<blockquote>"
                + escaped[2:]
                + "</blockquote>"
            )

        else:

            body_parts.append(
                "<p>"
                + escaped.replace(
                    "\n",
                    "<br>"
                )
                + "</p>"
            )

    document = f"""<!doctype html>
<html lang="hi">
<head>
<meta charset="utf-8">
<title>RAS Pre 2026 Knowledge Book</title>

<style>

@page {{
    size: A4;
    margin: 18mm;
}}

body {{
    font-family:
        "Noto Sans Devanagari",
        "Noto Sans",
        sans-serif;

    line-height: 1.65;
    font-size: 12pt;
    color: #222;
}}

h1 {{
    page-break-before: always;
    font-size: 25pt;
}}

h2 {{
    margin-top: 2em;
    font-size: 19pt;
}}

h3 {{
    font-size: 15pt;
}}

blockquote {{
    border-left: 4px solid #999;
    padding-left: 12px;
    color: #555;
}}

p {{
    text-align: justify;
}}

</style>

</head>

<body>

{''.join(body_parts)}

</body>
</html>
"""

    html_file = (
        OUTPUT
        / "RAS_Pre_2026_Book.html"
    )

    html_file.write_text(
        document,
        encoding="utf-8",
    )

    print(
        f"Created: {markdown_file}"
    )

    print(
        f"Created: {html_file}"
    )


if __name__ == "__main__":
    main()
