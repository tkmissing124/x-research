from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List

import requests

from .config import Settings


@dataclass(slots=True)
class GeneratedReport:
    text: str
    citations: List[str]
    tool_usage: Dict[str, Any]
    usage: Dict[str, Any]


class XAIMorningClient:
    base_url = "https://api.x.ai/v1/responses"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {settings.xai_api_key}",
                "Content-Type": "application/json",
                "User-Agent": "x-research-bot/1.0",
            }
        )

    def generate_report(self) -> GeneratedReport:
        if self.settings.dry_run:
            return self._build_mock_report()

        now = datetime.now().astimezone()
        start = now - timedelta(hours=self.settings.hours)
        from_date = start.date().isoformat()
        to_date = now.date().isoformat()

        tool: Dict[str, Any] = {
            "type": "x_search",
            "from_date": from_date,
            "to_date": to_date,
        }
        if self.settings.allowed_x_handles:
            tool["allowed_x_handles"] = self.settings.allowed_x_handles
        if self.settings.excluded_x_handles:
            tool["excluded_x_handles"] = self.settings.excluded_x_handles

        payload = {
            "model": self.settings.model,
            "max_turns": self.settings.max_turns,
            "include": ["no_inline_citations"],
            "tools": [tool],
            "input": self._build_prompt(now=now, start=start),
        }

        response = self.session.post(self.base_url, json=payload, timeout=180)
        if response.status_code >= 400:
            self._raise_api_error(response)
        body = response.json()

        text = self._extract_text(body)
        citations = self._extract_citations(body)
        tool_usage = body.get("server_side_tool_usage", {})
        usage = body.get("usage", {})
        return GeneratedReport(text=text, citations=citations, tool_usage=tool_usage, usage=usage)

    def _build_mock_report(self) -> GeneratedReport:
        now = datetime.now().astimezone()
        today_label = now.strftime("%Y-%m-%d")
        handle_line = ", ".join(self.settings.allowed_x_handles) if self.settings.allowed_x_handles else "公開X全体"
        text = f"""**🌅 Twitter {self.settings.topic} 朝刊 | {today_label}**

**1. 🤖 モック: エージェント開発ツールの話題**
- これは dry-run 用のモック出力です
- 実際の xAI API や x_search にはリクエストしていません
- allowed handles の設定は {handle_line} です

> なぜ注目すべきか：Slack への整形や定期実行の動作確認を、API課金なしで進められるため。

元投稿:
https://x.com/OpenAI/status/0000000000000000001
https://x.com/AnthropicAI/status/0000000000000000002

**2. 🧪 モック: コスト抑制設定の確認**
- XR_MAX_TURNS={self.settings.max_turns} の設定値が読み込まれています
- XR_POST_LINKS_PER_TOPIC={self.settings.post_links_per_topic} の設定値が読み込まれています
- XR_CLUSTER_COUNT={self.settings.cluster_count} の設定値が読み込まれています

> なぜ注目すべきか：実運用前に設定反映とSlack投稿の形を安全に確認できるため。

元投稿:
https://x.com/GoogleDeepMind/status/0000000000000000003
https://x.com/xai/status/0000000000000000004

**今日の観察**
- この出力は dry-run のモック結果です
- xAI API と x_search にはアクセスしていません
- 本番確認時は XR_DRY_RUN=false に切り替えてください
"""
        return GeneratedReport(
            text=text if text.endswith("\n") else text + "\n",
            citations=[],
            tool_usage={"x_search": 0, "mocked": True},
            usage={"mocked": True, "input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
        )

    def _build_prompt(self, now: datetime, start: datetime) -> str:
        language_hints = ", ".join(self.settings.language_hints) if self.settings.language_hints else "ja, en"
        today_label = now.strftime("%Y-%m-%d")
        return f"""
過去{self.settings.hours}時間以内のX上での{self.settings.topic}に関するトレンド、主要な議論、高頻出トピックを検索し、Slack に投稿できる形式の朝刊にまとめてください。

前提:
- 対象期間の目安: {start.isoformat()} から {now.isoformat()}
- x_search の検索範囲: {start.date().isoformat()} から {now.date().isoformat()}
- 優先言語: {language_hints}
- 想定読者: 投資家 + エンジニア
- 文体: 日本語、簡潔、情報密度高め、断定しすぎない

要件:
1. 過去{self.settings.hours}時間以内の内容を優先し、議論量が多く、拡散力が高く、明確なエンゲージメントがある話題を優先する
2. 散発的な投稿を列挙せず、まず 3〜{self.settings.cluster_count} 個の最注目トピックにまとめる
3. 各トピックには以下を含める
   - 明確なタイトル
   - 2〜4件の要点サマリー
   - 「なぜ注目すべきか」を1文で
   - 2〜{self.settings.post_links_per_topic}件の元投稿リンク
4. 影響力のあるアカウント、公式アカウント、主要関係者、または高エンゲージメントの投稿を優先する
5. 複数の投稿が同じ出来事について議論している場合は、一つのトピックにまとめ、重複させない
6. 大きなニュースがなくても、最も議論された話題を埋めて空白を作らない
7. 不確かな情報やゴシップは避け、未確認情報は未確認と明記する
8. 投資助言に見える表現は禁止する

出力形式:
- Slack対応のMarkdownを使う
- 各テーマに明確なタイトルと絵文字を付ける
- 投稿リンクは https://... 形式で直接記載する
- 表は使わず、短い箇条書き中心でまとめる
- 全体として「情報密度の高いコミュニティ朝刊」のようにまとめる
- 必ず最後に「今日の観察」を 2〜3 点つける

出力構造:
**🌅 Twitter {self.settings.topic} 朝刊 | {today_label}**

**1. {{トピックタイトル}}**
- 要点1
- 要点2
- 要点3

> なぜ注目すべきか：{{一文サマリー}}

元投稿:
https://x.com/...
https://x.com/...

**今日の観察**
- 観察1
- 観察2
""".strip()

    @staticmethod
    def _extract_text(body: Dict[str, Any]) -> str:
        output_text = body.get("output_text")
        if isinstance(output_text, str) and output_text.strip():
            return output_text.strip() + "\n"

        chunks: List[str] = []
        for item in body.get("output", []):
            if item.get("type") != "message":
                continue
            for content in item.get("content", []):
                if content.get("type") == "output_text" and content.get("text"):
                    chunks.append(content["text"])
        text = "\n".join(chunk.strip() for chunk in chunks if chunk.strip()).strip()
        if not text:
            raise RuntimeError("xAI response did not contain any output text")
        return text + "\n"

    @staticmethod
    def _extract_citations(body: Dict[str, Any]) -> List[str]:
        citations = []
        for item in body.get("citations", []):
            url = item.get("url")
            if url:
                citations.append(url)
        seen = set()
        unique = []
        for url in citations:
            if url not in seen:
                seen.add(url)
                unique.append(url)
        return unique

    @staticmethod
    def _raise_api_error(response: requests.Response) -> None:
        message = f"xAI responses API failed with status={response.status_code}"
        try:
            payload = response.json()
        except ValueError:
            payload = None

        if isinstance(payload, dict):
            detail = payload.get("error") or payload.get("detail") or payload.get("message")
            if isinstance(detail, dict):
                detail = detail.get("message") or str(detail)
            if detail:
                message += f": {detail}"
        raise RuntimeError(message)
