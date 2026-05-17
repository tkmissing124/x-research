from __future__ import annotations

from collections import Counter
from datetime import datetime
from typing import Iterable, List

from .config import Settings
from .models import TopicCluster, Tweet
from .cluster import extract_terms, normalize_text


def _format_metrics(tweet: Tweet) -> str:
    return (
        f"likes={tweet.metrics.get('like_count', 'unknown')}, "
        f"retweets={tweet.metrics.get('retweet_count', 'unknown')}, "
        f"replies={tweet.metrics.get('reply_count', 'unknown')}, "
        f"quotes={tweet.metrics.get('quote_count', 'unknown')}"
    )


def _summarize_cluster(cluster: TopicCluster) -> List[str]:
    points: List[str] = []
    top_tweets = cluster.tweets[:3]
    vocab = Counter()
    for tweet in top_tweets:
        vocab.update(extract_terms(normalize_text(tweet.text)))

    distilled = [term for term, _ in vocab.most_common(6) if term != cluster.label]
    if distilled:
        points.append(f"頻出キーワード: {', '.join(distilled[:4])}")

    for tweet in top_tweets[:2]:
        snippet = normalize_text(tweet.text)
        if len(snippet) > 180:
            snippet = snippet[:177] + "..."
        points.append(f"{tweet.username}: {snippet}")
    return points[:4]


def _why_it_matters(cluster: TopicCluster) -> str:
    top = cluster.tweets[0]
    if top.verified:
        return "公式または影響力のある発信源からの投稿が含まれ、二次拡散も起きているため。"
    return "同じ論点に複数投稿が集まり、エンゲージメントの総量が高いため。"


def _observations(clusters: List[TopicCluster]) -> List[str]:
    observations = []
    if not clusters:
        return ["過去24時間で大きな塊は少なく、分散的な議論が中心でした。"]

    verified_clusters = sum(1 for cluster in clusters if any(tweet.verified for tweet in cluster.tweets[:3]))
    if verified_clusters:
        observations.append(f"上位トピックのうち {verified_clusters} 件は公式または主要人物の発信が起点でした。")

    average_links = sum(len(cluster.tweets[:3]) for cluster in clusters) / len(clusters)
    if average_links >= 2:
        observations.append("単発のバズより、同一論点に複数ポストが重なるタイプの盛り上がりが目立ちました。")

    labels = [cluster.label for cluster in clusters[:3]]
    if labels:
        observations.append(f"今日の空気は {', '.join(labels)} あたりに集中しています。")

    return observations[:3]


def build_slack_markdown(clusters: List[TopicCluster], settings: Settings) -> str:
    today = datetime.now().strftime("%Y-%m-%d")
    lines = [f"**🌅 Twitter AI 朝刊 | {today}**", ""]

    for idx, cluster in enumerate(clusters, start=1):
        title = cluster.label.title() if cluster.label.isascii() else cluster.label
        lines.append(f"**{idx}. 🧠 {title}**")
        for point in _summarize_cluster(cluster):
            lines.append(f"- {point}")
        lines.append("")
        lines.append(f"> なぜ注目すべきか：{_why_it_matters(cluster)}")
        lines.append("")
        lines.append("元投稿：")
        for tweet in cluster.tweets[: settings.post_links_per_topic]:
            lines.append(f"{tweet.url}  ({_format_metrics(tweet)})")
        lines.append("")

    lines.append("**今日の観察**")
    for observation in _observations(clusters):
        lines.append(f"- {observation}")
    lines.append("")

    return "\n".join(lines).strip() + "\n"
