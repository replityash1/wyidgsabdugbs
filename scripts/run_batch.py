from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

import requests
import trafilatura
from bs4 import BeautifulSoup
from ddgs import DDGS


ROOT = Path(__file__).resolve().parents[1]

CONFIG = json.loads(
    (
        ROOT
        / "config"
        / "config.json"
    ).read_text(
        encoding="utf-8"
    )
)

SOURCES = {
    "tier_1": [
        "rpsc.rajasthan.gov.in",
        "rajasthan.gov.in",
        "jkk.artandculture.rajasthan.gov.in",
        "museumsrajasthan.rajasthan.gov.in",
        "tourism.rajasthan.gov.in",
        "foundation.rajasthan.gov.in",
        "assembly.rajasthan.gov.in",
        "rajassembly.nic.in",
        "rajbhawan.rajasthan.gov.in",
        "rajasthanhighcourt.nic.in",
        "finance.rajasthan.gov.in",
        "education.rajasthan.gov.in",
        "planning.rajasthan.gov.in",
        "des.rajasthan.gov.in",
        "agriculture.rajasthan.gov.in",
        "forest.rajasthan.gov.in",
        "water.rajasthan.gov.in",
        "asi.nic.in",
        "archives.gov.in",
        "nationalarchives.nic.in",
        "indiaculture.gov.in",
        "indiacode.nic.in",
        "pib.gov.in",
        "ncert.nic.in",
        "education.gov.in",
        "niti.gov.in",
        "rbi.org.in",
        "upsc.gov.in"
    ],

    "tier_2": [
        "ignca.gov.in",
        "sahitya-akademi.gov.in",
        "uniraj.ac.in",
        "jnu.ac.in",
        "du.ac.in",
        "iias.ac.in"
    ]
}


def allowed_domain(
    url: str,
    domains: list[str],
) -> bool:

    try:
        host = urlparse(url).hostname

        if not host:
            return False

        host = host.lower()

        return any(
            host == domain
            or host.endswith("." + domain)
            for domain in domains
        )

    except Exception:
        return False


def search_web(
    query: str,
    max_results: int,
) -> list[dict]:

    results = []

    try:

        with DDGS() as ddgs:

            for result in ddgs.text(
                query,
                max_results=max_results,
            ):

                results.append(result)

    except Exception as exc:

        print(
            f"Search failed: {exc}",
            file=sys.stderr,
        )

    return results


def fetch_page(
    url: str,
    max_chars: int,
) -> dict | None:

    try:

        response = requests.get(
            url,
            timeout=40,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 "
                    "(compatible; RASResearchBot/1.0)"
                )
            },
        )

        response.raise_for_status()

        html = response.text

        text = trafilatura.extract(
            html,
            include_tables=True,
            include_links=False,
            favor_precision=True,
        )

        if not text:
            return None

        text = text[:max_chars]

        soup = BeautifulSoup(
            html,
            "html.parser",
        )

        image_url = None

        meta = soup.find(
            "meta",
            attrs={
                "property": "og:image"
            },
        )

        if meta:
            image_url = meta.get(
                "content"
            )

        return {
            "url": url,
            "title": (
                soup.title.string.strip()
                if soup.title
                and soup.title.string
                else url
            ),
            "text": text,
            "image_url": image_url,
        }

    except Exception as exc:

        print(
            f"Fetch failed {url}: {exc}",
            file=sys.stderr,
        )

        return None


def research_topic(
    topic: dict,
) -> dict:

    searches = []

    hi = topic[
        "topic_title_hi"
    ]

    en = topic[
        "topic_title_en"
    ]

    searches.extend(
        [
            f'"{hi}" Rajasthan',
            f'"{hi}" राजस्थान',
            f'"{en}" Rajasthan',
            f'"{en}" Rajasthan government',
            f'"{hi}" archaeological history Rajasthan',
            f'"{en}" Rajasthan history research',
        ]
    )

    max_results = CONFIG[
        "research"
    ][
        "results_per_query"
    ]

    max_sources = CONFIG[
        "research"
    ][
        "max_sources_per_topic"
    ]

    max_chars = CONFIG[
        "research"
    ][
        "max_source_chars"
    ]

    candidates = []

    for tier_name in (
        "tier_1",
        "tier_2",
    ):

        domains = SOURCES[
            tier_name
        ]

        found_urls = set()

        for query in searches:

            results = search_web(
                query,
                max_results,
            )

            for result in results:

                url = result.get(
                    "href"
                ) or result.get(
                    "url"
                )

                if not url:
                    continue

                if not allowed_domain(
                    url,
                    domains,
                ):
                    continue

                if url in found_urls:
                    continue

                found_urls.add(url)

                candidates.append(
                    (
                        1
                        if tier_name
                        == "tier_1"
                        else 2,
                        url,
                        result.get(
                            "title",
                            "",
                        ),
                        result.get(
                            "body",
                            "",
                        ),
                    )
                )

                if len(candidates) >= max_sources:
                    break

            if len(candidates) >= max_sources:
                break

        if len(candidates) >= max_sources:
            break

    sources = []

    for index, item in enumerate(
        candidates,
        start=1,
    ):

        tier, url, title, snippet = item

        print(
            f"Fetching source {index}: {url}"
        )

        page = fetch_page(
            url,
            max_chars,
        )

        if not page:
            continue

        source_id = f"S{len(sources) + 1}"

        sources.append(
            {
                "id": source_id,
                "tier": tier,
                "title": page[
                    "title"
                ] or title,
                "url": url,
                "domain": (
                    urlparse(url).hostname
                    or ""
                ),
                "snippet": snippet,
                "content": page["text"],
                "image_url": page[
                    "image_url"
                ],
            }
        )

        if len(sources) >= max_sources:
            break

    return {
        "topic": topic,
        "sources": sources,
    }


def clean_json(
    text: str,
) -> dict:

    text = text.strip()

    text = re.sub(
        r"^```json\s*",
        "",
        text,
        flags=re.I,
    )

    text = re.sub(
        r"^```\s*",
        "",
        text,
    )

    text = re.sub(
        r"\s*```$",
        "",
        text,
    )

    start = text.find("{")
    end = text.rfind("}")

    if start < 0 or end < start:
        raise ValueError(
            "No JSON object found."
        )

    return json.loads(
        text[start:end + 1]
    )


def ask_llama(
    prompt: str,
) -> str:

    payload = {
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a rigorous research "
                    "assistant. Follow the user's "
                    "output format exactly."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        "temperature": 0.15,
        "max_tokens": 7000,
        "stream": False,
    }

    response = requests.post(
        "http://127.0.0.1:8080/v1/chat/completions",
        json=payload,
        timeout=900,
    )

    response.raise_for_status()

    data = response.json()

    return (
        data["choices"][0]
        ["message"]["content"]
    )


def load_prompt(
    name: str,
) -> str:

    return (
        ROOT
        / "prompts"
        / name
    ).read_text(
        encoding="utf-8"
    )


def run_research(
    topic: dict,
    source_package: dict,
) -> dict:

    prompt = (
        load_prompt("research.txt")
        + "\n\n"
        + "TOPIC:\n"
        + json.dumps(
            topic,
            ensure_ascii=False,
            indent=2,
        )
        + "\n\nSOURCE PACKAGE:\n"
        + json.dumps(
            source_package,
            ensure_ascii=False,
            indent=2,
        )
    )

    for attempt in range(3):

        try:

            result = ask_llama(
                prompt
            )

            return clean_json(
                result
            )

        except Exception as exc:

            print(
                f"Research attempt "
                f"{attempt + 1} failed: {exc}",
                file=sys.stderr,
            )

            if attempt == 2:
                raise

            time.sleep(
                5 * (attempt + 1)
            )

    raise RuntimeError(
        "Research failed."
    )


def run_writer(
    topic: dict,
    research: dict,
    source_package: dict,
) -> str:

    prompt = (
        load_prompt("chapter.txt")
        + "\n\n"
        + "TOPIC:\n"
        + json.dumps(
            topic,
            ensure_ascii=False,
            indent=2,
        )
        + "\n\nRESEARCH:\n"
        + json.dumps(
            research,
            ensure_ascii=False,
            indent=2,
        )
        + "\n\nSOURCE RECORDS:\n"
        + json.dumps(
            source_package,
            ensure_ascii=False,
            indent=2,
        )
    )

    for attempt in range(3):

        try:

            return ask_llama(
                prompt
            )

        except Exception as exc:

            print(
                f"Writer attempt "
                f"{attempt + 1} failed: {exc}",
                file=sys.stderr,
            )

            if attempt == 2:
                raise

            time.sleep(
                5 * (attempt + 1)
            )

    raise RuntimeError(
        "Writer failed."
    )


def local_audit(
    topic: dict,
    research: dict,
    chapter: str,
) -> dict:

    valid_sources = {
        source["id"]
        for source in research.get(
            "sources",
            [],
        )
    }

    cited = set(
        re.findall(
            r"\[(S\d+)\]",
            chapter,
        )
    )

    invalid = sorted(
        cited - valid_sources
    )

    missing_citation_sections = []

    paragraphs = [
        p.strip()
        for p in chapter.split("\n\n")
        if p.strip()
    ]

    for paragraph in paragraphs:

        if (
            len(paragraph) > 250
            and not paragraph.startswith(
                "#"
            )
            and "[UNVERIFIED]" not in paragraph
            and not re.search(
                r"\[S\d+\]",
                paragraph,
            )
        ):
            missing_citation_sections.append(
                paragraph[:180]
            )

    return {
        "topic_id": topic[
            "topic_id"
        ],
        "invalid_source_ids": invalid,
        "uncited_long_sections": (
            missing_citation_sections
        ),
        "citation_score": (
            100
            if not invalid
            and not missing_citation_sections
            else 70
        ),
        "status": (
            "PASS"
            if not invalid
            and not missing_citation_sections
            else "REVISE"
        ),
    }


def main() -> None:

    if len(sys.argv) != 2:
        raise SystemExit(
            "Usage: run_batch.py BATCH_ID"
        )

    batch_id = int(
        sys.argv[1]
    )

    topics = json.loads(
        (
            ROOT
            / "work"
            / "topics.json"
        ).read_text(
            encoding="utf-8"
        )
    )

    batches = json.loads(
        (
            ROOT
            / "work"
            / "batches.json"
        ).read_text(
            encoding="utf-8"
        )
    )

    batch = next(
        item
        for item in batches
        if item["batch_id"] == batch_id
    )

    topic_map = {
        topic["topic_id"]: topic
        for topic in topics
    }

    output = (
        ROOT
        / "work"
        / "results"
    )

    output.mkdir(
        parents=True,
        exist_ok=True,
    )

    for topic_id in batch[
        "topic_ids"
    ]:

        topic = topic_map[
            topic_id
        ]

        print(
            "\n=================================="
        )
        print(
            f"TOPIC: {topic['topic_title_en']}"
        )
        print(
            "=================================="
        )

        source_package = research_topic(
            topic
        )

        print(
            f"Sources retrieved: "
            f"{len(source_package['sources'])}"
        )

        research = run_research(
            topic,
            source_package,
        )

        chapter = run_writer(
            topic,
            research,
            source_package,
        )

        audit = local_audit(
            topic,
            research,
            chapter,
        )

        topic_dir = (
            output
            / topic_id
        )

        topic_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        (
            topic_dir
            / "research.json"
        ).write_text(
            json.dumps(
                research,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        (
            topic_dir
            / "sources.json"
        ).write_text(
            json.dumps(
                source_package,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        (
            topic_dir
            / "chapter.md"
        ).write_text(
            chapter,
            encoding="utf-8",
        )

        (
            topic_dir
            / "audit.json"
        ).write_text(
            json.dumps(
                audit,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        print(
            f"Finished: {topic_id}"
        )

    print(
        f"\nBatch {batch_id} complete."
    )


if __name__ == "__main__":
    main()
