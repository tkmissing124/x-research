from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List


@dataclass(slots=True)
class Tweet:
    id: str
    text: str
    author_id: str
    username: str
    created_at: datetime
    query: str
    metrics: Dict[str, int]
    verified: bool = False

    @property
    def url(self) -> str:
        return f"https://x.com/{self.username}/status/{self.id}"

    @property
    def engagement_score(self) -> float:
        return (
            self.metrics.get("like_count", 0) * 1.0
            + self.metrics.get("retweet_count", 0) * 2.0
            + self.metrics.get("reply_count", 0) * 1.5
            + self.metrics.get("quote_count", 0) * 1.5
        )


@dataclass(slots=True)
class TopicCluster:
    label: str
    phrase_hints: List[str]
    tweets: List[Tweet] = field(default_factory=list)

    @property
    def score(self) -> float:
        return sum(tweet.engagement_score for tweet in self.tweets)
