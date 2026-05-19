from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import List


@dataclass(slots=True)
class Settings:
    xai_api_key: str
    slack_webhook_url: str
    topic: str
    hours: int
    cluster_count: int
    post_links_per_topic: int
    language_hints: List[str]
    allowed_x_handles: List[str]
    excluded_x_handles: List[str]
    model: str
    max_turns: int
    dry_run: bool


def _load_dotenv() -> None:
    env_path = Path.cwd() / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def _get_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _split_csv(value: str | None) -> List[str]:
    if not value:
        return []
    return [part.strip() for part in value.split(",") if part.strip()]


def load_settings() -> Settings:
    _load_dotenv()

    xai_api_key = os.getenv("XAI_API_KEY", "").strip()
    legacy_x_token = os.getenv("X_BEARER_TOKEN", "").strip()
    slack_webhook_url = os.getenv("SLACK_WEBHOOK_URL", "").strip()
    topic = os.getenv("XR_TOPIC", "AI").strip() or "AI"
    hours = int(os.getenv("XR_HOURS", "24"))
    cluster_count = int(os.getenv("XR_CLUSTER_COUNT", "4"))
    post_links_per_topic = int(os.getenv("XR_POST_LINKS_PER_TOPIC", "3"))
    language_hints = _split_csv(os.getenv("XR_LANGUAGE_HINTS", "ja,en"))
    allowed_x_handles = _split_csv(os.getenv("XR_ALLOWED_X_HANDLES"))
    excluded_x_handles = _split_csv(os.getenv("XR_EXCLUDED_X_HANDLES"))
    model = os.getenv("XR_MODEL", "grok-4.3").strip() or "grok-4.3"
    max_turns = int(os.getenv("XR_MAX_TURNS", "2"))
    dry_run = _get_bool("XR_DRY_RUN", False)

    if not xai_api_key and not dry_run:
        if legacy_x_token:
            raise ValueError(
                "XAI_API_KEY is required. X_BEARER_TOKEN is an X API token and cannot be used for Grok x_search."
            )
        raise ValueError("XAI_API_KEY is required")
    if not slack_webhook_url:
        raise ValueError("SLACK_WEBHOOK_URL is required")

    return Settings(
        xai_api_key=xai_api_key,
        slack_webhook_url=slack_webhook_url,
        topic=topic,
        hours=hours,
        cluster_count=cluster_count,
        post_links_per_topic=post_links_per_topic,
        language_hints=language_hints,
        allowed_x_handles=allowed_x_handles,
        excluded_x_handles=excluded_x_handles,
        model=model,
        max_turns=max_turns,
        dry_run=dry_run,
    )
