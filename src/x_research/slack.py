from __future__ import annotations

import requests


class SlackWebhookClient:
    def __init__(self, webhook_url: str) -> None:
        self.webhook_url = webhook_url

    def post_markdown(self, text: str) -> None:
        response = requests.post(
            self.webhook_url,
            json={"text": text},
            timeout=30,
        )
        if response.status_code >= 400:
            detail = response.text.strip()
            raise RuntimeError(
                f"Slack webhook failed with status={response.status_code}: {detail}"
            )
