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
    source_mode: str
    official_x_handles: List[str]
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


def _get_source_mode() -> str:
    value = (os.getenv("XR_SOURCE_MODE", "mixed").strip().lower() or "mixed")
    allowed_values = {"official", "mixed", "discovery"}
    if value not in allowed_values:
        choices = ", ".join(sorted(allowed_values))
        raise ValueError(f"XR_SOURCE_MODE must be one of: {choices}")
    return value


def load_settings() -> Settings:
    _load_dotenv()

    xai_api_key = os.getenv("XAI_API_KEY", "").strip()
    slack_webhook_url = os.getenv("SLACK_WEBHOOK_URL", "").strip()
    topic = os.getenv("XR_TOPIC", "AI").strip() or "AI"
    hours = int(os.getenv("XR_HOURS", "24"))
    cluster_count = int(os.getenv("XR_CLUSTER_COUNT", "3"))
    post_links_per_topic = int(os.getenv("XR_POST_LINKS_PER_TOPIC", "2"))
    language_hints = _split_csv(os.getenv("XR_LANGUAGE_HINTS", "ja,en"))
    source_mode = _get_source_mode()
    official_x_handles = _split_csv(
        os.getenv("XR_OFFICIAL_X_HANDLES", "OpenAI,AnthropicAI,GoogleDeepMind,xAI,GoogleAI")
    )
    allowed_x_handles = _split_csv(os.getenv("XR_ALLOWED_X_HANDLES"))
    excluded_x_handles = _split_csv(os.getenv("XR_EXCLUDED_X_HANDLES"))
    model = os.getenv("XR_MODEL", "grok-4.3").strip() or "grok-4.3"
    max_turns = int(os.getenv("XR_MAX_TURNS", "2"))
    dry_run = _get_bool("XR_DRY_RUN", False)

    if not xai_api_key and not dry_run:
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
        source_mode=source_mode,
        official_x_handles=official_x_handles,
        allowed_x_handles=allowed_x_handles,
        excluded_x_handles=excluded_x_handles,
        model=model,
        max_turns=max_turns,
        dry_run=dry_run,
    )
