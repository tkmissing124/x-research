from __future__ import annotations

import sys
import traceback

from .config import load_settings
from .slack import SlackWebhookClient
from .x_client import XAIMorningClient


def main() -> int:
    try:
        settings = load_settings()
        print(
            "Starting Grok batch "
            f"topic={settings.topic} hours={settings.hours} model={settings.model} "
            f"source_mode={settings.source_mode} max_turns={settings.max_turns} "
            f"dry_run={settings.dry_run}"
        )
        if settings.priority_x_handles:
            print(f"priority x handles: {', '.join(settings.priority_x_handles)}")
        if settings.allowed_x_handles and settings.source_mode != "official":
            print(
                "XR_ALLOWED_X_HANDLES is set, so search remains hard-filtered to those handles "
                "even though source_mode is not official."
            )

        client = XAIMorningClient(settings)
        report = client.generate_report()

        x_search_calls = report.tool_usage.get("x_search", 0)
        if report.tool_usage.get("mocked"):
            print("dry-run mock mode enabled: xAI API was not called.")
        if x_search_calls:
            print(f"x_search tool calls: {x_search_calls}")
        if report.usage:
            print(f"token usage: {report.usage}")
        if report.citations:
            print(f"citations captured: {len(report.citations)}")

        slack = SlackWebhookClient(settings.slack_webhook_url)
        slack.post_markdown(report.text)
        print("Posted morning report to Slack.")
        sys.stdout.write(report.text)
        return 0
    except Exception as exc:
        print(f"Batch failed: {exc}", file=sys.stderr)
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
