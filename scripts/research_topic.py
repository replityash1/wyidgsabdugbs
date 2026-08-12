from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import requests


ROOT = Path(__file__).resolve().parents[1]

TOPICS_FILE = ROOT / "work" / "topics.json"
SETTINGS_FILE = ROOT / "config" / "settings.json"
SOURCES_FILE = ROOT / "config" / "sources.json"
PROMPT_FILE = ROOT / "prompts" / "researcher.txt"


def load_json(path: Path) -> Any:
    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


def tavily_search(
    query: str,
    api_key: str,
    domains: list[str],
    max_results: int = 8,
) -> list[dict[str, Any]]:

    response = requests.post(
        "https://api.tavily.com/search",
        json={
            "api_key": api_key,
            "query": query,
            "search_depth": "advanced",
            "max_results": max_results,
            "include_answer": False,
            "include_raw_content": True,
            "include_images": True,
            "include_domains": domains,
        },
        timeout=120,
    )

    response.raise_for_status()

    data = response.json()

    return data.get("results", [])


def build_search_queries(topic: dict[str, Any]) -> list[str]:

    hi = topic["topic_title_hi"]
    en = topic["topic_title_en"]

    return [
        f'"{hi}" Rajasthan official',
        f'"{en}" Rajasthan government',
        f'"{hi}" राजस्थान इतिहास',
        f'"{en}" archaeology Rajasthan',
        f'"{en}" historical research Rajasthan',
    ]


def collect_sources(
    topic: dict[str, Any],
    api_key: str,
    source_config: dict[str, Any],
    settings: dict[str, Any],
) -> list[dict[str, Any]]:

    domains = (
        source_config["tier_1_official"]
        + source_config["tier_2_academic"]
    )

    results: list[dict[str, Any]] = []

    seen: set[str] = set()

    queries = build_search_queries(topic)

    for query in queries:

        try:
            found = tavily_search(
                query,
                api_key,
                domains,
                max_results=settings[
                    "maximum_sources_per_topic"
                ],
            )

        except Exception as exc:
            print(
                f"Search failed: {query}: {exc}",
                file=sys.stderr,
            )
            continue

        for item in found:

            url = item.get("url", "").strip()

            if not url or url in seen:
                continue

            seen.add(url)

            results.append(
                {
                    "title": item.get(
                        "title",
                        "",
                    ),
                    "url": url,
                    "domain": item.get(
                        "url",
                        "",
                    ).split("/")[2]
                    if "://" in url
                    else "",
                    "content": item.get(
                        "raw_content"
                    )
                    or item.get(
                        "content",
                        "",
                    ),
                    "snippet": item.get(
                        "content",
                        "",
                    ),
                    "images": item.get(
                        "images",
                        [],
                    ),
                }
            )

            if len(results) >= settings[
                "maximum_sources_per_topic"
            ]:
                return results

    return results


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
                "temperature": 0.15,
                "responseMimeType": "application/json",
            },
        },
        timeout=600,
    )

    response.raise_for_status()

    data = response.json()

    try:
        return (
            data["candidates"][0]
            ["content"]["parts"][0]
            ["text"]
        )

    except (
        KeyError,
        IndexError,
        TypeError,
    ) as exc:

        raise RuntimeError(
            f"Unexpected Gemini response: {data}"
        ) from exc


def main() -> None:

    if len(sys.argv) != 2:
        raise SystemExit(
            "Usage: research_topic.py TOPIC_ID"
        )

    topic_id = sys.argv[1]

    topics = load_json(TOPICS_FILE)
    settings = load_json(SETTINGS_FILE)
    source_config = load_json(SOURCES_FILE)

    topic = next(
        (
            item
            for item in topics
            if item["topic_id"] == topic_id
        ),
        None,
    )

    if topic is None:
        raise SystemExit(
            f"Topic not found: {topic_id}"
        )

    tavily_key = os.environ.get(
        "TAVILY_API_KEY"
    )

    gemini_key = os.environ.get(
        "GEMINI_API_KEY"
    )

    if not tavily_key:
        raise SystemExit(
            "TAVILY_API_KEY is missing."
        )

    if not gemini_key:
        raise SystemExit(
            "GEMINI_API_KEY is missing."
        )

    print(
        f"Researching: "
        f"{topic['topic_title_en']}"
    )

    sources = collect_sources(
        topic,
        tavily_key,
        source_config,
        settings,
    )

    print(
        f"Collected {len(sources)} source candidates."
    )

    prompt_template = PROMPT_FILE.read_text(
        encoding="utf-8"
    )

    source_payload = json.dumps(
        {
            "topic": topic,
            "sources": sources,
        },
        ensure_ascii=False,
        indent=2,
    )

    final_prompt = (
        prompt_template
        + "\n\n"
        + "==================================================\n"
        + "RESEARCH INPUT\n"
        + "==================================================\n\n"
        + source_payload
    )

    for attempt in range(3):

        try:

            result = gemini_generate(
                final_prompt,
                settings["research_model"],
                gemini_key,
            )

            parsed = json.loads(result)

            break

        except Exception as exc:

            print(
                f"Gemini attempt {attempt + 1} failed: {exc}",
                file=sys.stderr,
            )

            if attempt == 2:
                raise

            time.sleep(
                5 * (attempt + 1)
            )

    output_dir = (
        ROOT
        / "work"
        / "research"
        / topic_id
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    (output_dir / "research.json").write_text(
        json.dumps(
            parsed,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    (output_dir / "raw_sources.json").write_text(
        json.dumps(
            sources,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(
        f"Research saved: {output_dir}"
    )


if __name__ == "__main__":
    main()
