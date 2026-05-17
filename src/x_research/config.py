from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List


DEFAULT_QUERIES = [
    'OpenAI OR ChatGPT OR "GPT-5" OR "GPT 5" -is:retweet',
    'Anthropic OR Claude OR "Claude Code" -is:retweet',
    'Google AI OR Gemini OR DeepMind OR Veo OR Imagen -is:retweet',
    'xAI OR Grok OR "grok 3" OR colossus -is:retweet',
    'Meta AI OR Llama OR SAM OR "segment anything" -is:retweet',
    'Microsoft AI OR Copilot OR Phi OR Azure OpenAI -is:retweet',
    'Cursor OR Windsurf OR Replit OR Lovable OR Bolt.new -is:retweet',
    'MCP OR "Model Context Protocol" OR "AI agent" -is:retweet',
    '"open source model" OR DeepSeek OR Qwen OR Mistral -is:retweet',
    '"AI image" OR "image generation" OR Flux OR Midjourney -is:retweet',
    '"AI video" OR Runway OR Sora OR Kling -is:retweet',
    '"AI safety" OR alignment OR policy OR regulation -is:retweet',
    'benchmark OR evals OR hallucination OR reasoning model -is:retweet',
    'startup AND AI AND funding -is:retweet',
]


@dataclass(slots=True)
class Settings:
    x_bearer_token: str
    slack_webhook_url: str
    topic: str
    hours: int
    max_results_per_query: int
    cluster_count: int
    post_links_per_topic: int
    language_hints: List[str]
    queries: List[str]
    dry_run: bool


def _get_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _split_csv(value: str | None) -> List[str]:
    if not value:
        return []
    return [part.strip() for part in value.split(",") if part.strip()]


def _split_lines(value: str | None) -> List[str]:
    if not value:
        return []
    return [line.strip() for line in value.splitlines() if line.strip()]


def build_queries(topic: str, language_hints: List[str], extra_queries: List[str]) -> List[str]:
    lang_filters = []
    for lang in language_hints:
        lang_filters.append(f"lang:{lang}")
    lang_clause = ""
    if lang_filters:
        lang_clause = " (" + " OR ".join(lang_filters) + ")"

    queries = []
    for query in DEFAULT_QUERIES:
        if lang_clause:
            queries.append(f"({query}){lang_clause}")
        else:
            queries.append(query)

    if topic and topic.strip().lower() not in {"ai", "artificial intelligence"}:
        topic_query = f'("{topic.strip()}" OR {topic.strip()}) -is:retweet'
        if lang_clause:
            topic_query = f"({topic_query}){lang_clause}"
        queries.insert(0, topic_query)

    queries.extend(extra_queries)
    seen = set()
    unique_queries = []
    for query in queries:
        if query not in seen:
            seen.add(query)
            unique_queries.append(query)
    return unique_queries


def load_settings() -> Settings:
    x_bearer_token = os.getenv("X_BEARER_TOKEN", "").strip()
    slack_webhook_url = os.getenv("SLACK_WEBHOOK_URL", "").strip()
    topic = os.getenv("XR_TOPIC", "AI").strip() or "AI"
    hours = int(os.getenv("XR_HOURS", "24"))
    max_results_per_query = int(os.getenv("XR_MAX_RESULTS_PER_QUERY", "50"))
    cluster_count = int(os.getenv("XR_CLUSTER_COUNT", "4"))
    post_links_per_topic = int(os.getenv("XR_POST_LINKS_PER_TOPIC", "3"))
    language_hints = _split_csv(os.getenv("XR_LANGUAGE_HINTS", "ja,en"))
    extra_queries = _split_lines(os.getenv("XR_EXTRA_QUERIES"))
    queries = build_queries(topic, language_hints, extra_queries)
    dry_run = _get_bool("XR_DRY_RUN", False)

    if not x_bearer_token:
        raise ValueError("X_BEARER_TOKEN is required")
    if not slack_webhook_url and not dry_run:
        raise ValueError("SLACK_WEBHOOK_URL is required unless XR_DRY_RUN=true")

    return Settings(
        x_bearer_token=x_bearer_token,
        slack_webhook_url=slack_webhook_url,
        topic=topic,
        hours=hours,
        max_results_per_query=max_results_per_query,
        cluster_count=cluster_count,
        post_links_per_topic=post_links_per_topic,
        language_hints=language_hints,
        queries=queries,
        dry_run=dry_run,
    )
