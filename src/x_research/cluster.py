from __future__ import annotations

import re
from collections import Counter, defaultdict
from typing import Dict, Iterable, List, Sequence, Set, Tuple

from .models import TopicCluster, Tweet


STOPWORDS = {
    "the", "and", "for", "with", "this", "that", "from", "into", "about", "after", "over",
    "under", "have", "just", "more", "than", "when", "what", "your", "will", "they", "their",
    "there", "here", "also", "been", "being", "would", "could", "should", "today", "yesterday",
    "launch", "launched", "using", "used", "new", "now", "you", "our", "out", "all", "one",
    "openai", "anthropic", "google", "meta", "microsoft", "xai", "grok", "claude", "gemini",
    "chatgpt", "copilot", "llm", "ai",
}

TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9_\-\.]{2,}|[\u3040-\u30ff\u4e00-\u9fff]{2,}")
URL_RE = re.compile(r"https?://\S+")
MENTION_RE = re.compile(r"@([A-Za-z0-9_]+)")
HASHTAG_RE = re.compile(r"#([A-Za-z0-9_\-]+)")


def normalize_text(text: str) -> str:
    text = URL_RE.sub(" ", text)
    text = text.replace("\n", " ")
    return re.sub(r"\s+", " ", text).strip()


def extract_terms(text: str) -> Set[str]:
    terms: Set[str] = set()

    for mention in MENTION_RE.findall(text):
        if len(mention) >= 3:
            terms.add(mention.lower())
    for hashtag in HASHTAG_RE.findall(text):
        if len(hashtag) >= 3:
            terms.add(hashtag.lower())

    tokens = TOKEN_RE.findall(text)
    lowered = [token.lower() for token in tokens]
    for token in lowered:
        if token in STOPWORDS or token.isdigit() or len(token) < 3:
            continue
        terms.add(token)

    for idx in range(len(lowered) - 1):
        a = lowered[idx]
        b = lowered[idx + 1]
        if a in STOPWORDS or b in STOPWORDS:
            continue
        if len(a) < 3 or len(b) < 3:
            continue
        terms.add(f"{a} {b}")

    return terms


def select_cluster_labels(tweets: Sequence[Tweet], cluster_count: int) -> List[Tuple[str, List[str]]]:
    doc_freq = Counter()
    examples: Dict[str, Counter] = defaultdict(Counter)

    for tweet in tweets[:200]:
        text = normalize_text(tweet.text)
        terms = extract_terms(text)
        weighted = max(1, round(tweet.engagement_score / 50))
        for term in terms:
            doc_freq[term] += weighted
            examples[term][tweet.query] += weighted

    labels: List[Tuple[str, List[str]]] = []
    used_tokens: Set[str] = set()
    for term, _ in doc_freq.most_common(50):
        parts = term.split()
        if any(part in used_tokens for part in parts if len(parts) == 1):
            continue
        if len(parts) == 1 and doc_freq[term] < 3:
            continue
        if len(parts) > 1 and doc_freq[term] < 2:
            continue
        hint_queries = [query for query, _ in examples[term].most_common(3)]
        labels.append((term, hint_queries))
        for part in parts:
            used_tokens.add(part)
        if len(labels) >= cluster_count:
            break

    if not labels:
        for tweet in tweets[:cluster_count]:
            labels.append((tweet.query[:60], [tweet.query]))
    return labels


def assign_clusters(tweets: Sequence[Tweet], cluster_count: int) -> List[TopicCluster]:
    labels = select_cluster_labels(tweets, cluster_count)
    clusters = [TopicCluster(label=label, phrase_hints=hints) for label, hints in labels]

    for tweet in tweets:
        text = normalize_text(tweet.text)
        terms = extract_terms(text)
        best_index = None
        best_score = 0
        for idx, cluster in enumerate(clusters):
            label_terms = set(cluster.label.split())
            score = 0
            if cluster.label in terms:
                score += 3
            score += len(label_terms & terms)
            if cluster.phrase_hints and tweet.query in cluster.phrase_hints:
                score += 1
            if score > best_score:
                best_score = score
                best_index = idx
        if best_index is not None and best_score > 0:
            clusters[best_index].tweets.append(tweet)

    leftovers = [tweet for tweet in tweets if all(tweet not in cluster.tweets for cluster in clusters)]
    for tweet in leftovers[: max(0, cluster_count * 2)]:
        if clusters:
            min_cluster = min(clusters, key=lambda item: len(item.tweets))
            min_cluster.tweets.append(tweet)

    cleaned: List[TopicCluster] = []
    for cluster in clusters:
        if not cluster.tweets:
            continue
        unique = {tweet.id: tweet for tweet in cluster.tweets}
        cluster.tweets = sorted(unique.values(), key=lambda item: (item.engagement_score, item.created_at), reverse=True)
        cleaned.append(cluster)

    cleaned.sort(key=lambda item: item.score, reverse=True)
    return cleaned[:cluster_count]
