from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Dict, List

import requests

from .config import Settings
from .models import Tweet


class XRecentSearchClient:
    base_url = "https://api.x.com/2/tweets/search/recent"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {settings.x_bearer_token}",
                "User-Agent": "x-research-bot/1.0",
            }
        )

    def fetch_recent(self) -> List[Tweet]:
        end_time = datetime.now(timezone.utc) - timedelta(seconds=30)
        start_time = end_time - timedelta(hours=self.settings.hours)

        all_tweets: Dict[str, Tweet] = {}
        for query in self.settings.queries:
            for tweet in self._search_query(query, start_time, end_time):
                existing = all_tweets.get(tweet.id)
                if existing is None or tweet.engagement_score > existing.engagement_score:
                    all_tweets[tweet.id] = tweet

        tweets = list(all_tweets.values())
        tweets.sort(key=lambda item: (item.engagement_score, item.created_at), reverse=True)
        return tweets

    def _search_query(
        self,
        query: str,
        start_time: datetime,
        end_time: datetime,
    ) -> List[Tweet]:
        tweets: List[Tweet] = []
        next_token = None
        seen = set()

        while True:
            params = {
                "query": query,
                "max_results": min(self.settings.max_results_per_query, 100),
                "start_time": start_time.isoformat().replace("+00:00", "Z"),
                "end_time": end_time.isoformat().replace("+00:00", "Z"),
                "tweet.fields": "created_at,public_metrics,author_id,lang",
                "expansions": "author_id",
                "user.fields": "username,verified",
                "sort_order": "recency",
            }
            if next_token:
                params["next_token"] = next_token

            response = self.session.get(self.base_url, params=params, timeout=30)
            if response.status_code >= 400:
                self._raise_api_error(response, query)
            payload = response.json()

            users = {
                user["id"]: {
                    "username": user.get("username", "unknown"),
                    "verified": user.get("verified", False),
                }
                for user in payload.get("includes", {}).get("users", [])
            }

            for item in payload.get("data", []):
                tweet_id = item["id"]
                if tweet_id in seen:
                    continue
                seen.add(tweet_id)
                user = users.get(item["author_id"], {"username": "unknown", "verified": False})
                tweets.append(
                    Tweet(
                        id=tweet_id,
                        text=item.get("text", ""),
                        author_id=item.get("author_id", ""),
                        username=user["username"],
                        created_at=datetime.fromisoformat(item["created_at"].replace("Z", "+00:00")),
                        query=query,
                        metrics=item.get("public_metrics", {}),
                        verified=user["verified"],
                    )
                )

            next_token = payload.get("meta", {}).get("next_token")
            if not next_token or len(tweets) >= self.settings.max_results_per_query:
                break

        tweets.sort(key=lambda item: (item.engagement_score, item.created_at), reverse=True)
        return tweets[: self.settings.max_results_per_query]

    @staticmethod
    def _raise_api_error(response: requests.Response, query: str) -> None:
        message = f"X recent search failed with status={response.status_code}"
        try:
            payload = response.json()
        except ValueError:
            payload = None

        if isinstance(payload, dict):
            errors = payload.get("errors") or []
            if errors:
                first = errors[0]
                detail = first.get("detail") or first.get("message") or str(first)
                message += f": {detail}"
            elif payload.get("detail"):
                message += f": {payload['detail']}"

        message += f" | query={query}"
        if response.status_code in {401, 403}:
            message += " | Check that X_BEARER_TOKEN is a Bearer Token, not an API key or client secret."
        raise RuntimeError(message)
