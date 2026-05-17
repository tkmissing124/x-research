from __future__ import annotations

import sys

from .cluster import assign_clusters
from .config import load_settings
from .render import build_slack_markdown
from .slack import SlackWebhookClient
from .x_client import XRecentSearchClient


def main() -> int:
    settings = load_settings()
    client = XRecentSearchClient(settings)
    tweets = client.fetch_recent()

    if not tweets:
        print("No tweets found in the selected time window.")
        return 0

    clusters = assign_clusters(tweets, settings.cluster_count)
    message = build_slack_markdown(clusters, settings)

    if settings.dry_run:
        sys.stdout.write(message)
        return 0

    slack = SlackWebhookClient(settings.slack_webhook_url)
    slack.post_markdown(message)
    print(f"Posted {len(clusters)} topics to Slack.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
