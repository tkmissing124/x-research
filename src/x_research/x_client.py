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
        effective_allowed_handles = self._effective_allowed_x_handles()
        if effective_allowed_handles:
            tool["allowed_x_handles"] = effective_allowed_handles
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
        effective_allowed_handles = self._effective_allowed_x_handles()
        handle_line = (
            ", ".join(effective_allowed_handles)
            if effective_allowed_handles
            else "公開X全体"
        )
        priority_line = (
            ", ".join(self.settings.priority_x_handles)
            if self.settings.priority_x_handles
            else "なし"
        )
        text = f"""**🌅 Twitter {self.settings.topic} 朝刊 | {today_label}**

**1. 🤖 モック: エージェント開発ツールの話題**
- これは dry-run 用のモック出力です
- 実際の xAI API や x_search にはリクエストしていません
- source_mode は {self.settings.source_mode} です
- 有効な allowed handles は {handle_line} です
- 重点観測する非公式アカウントは {priority_line} です

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

    def _effective_allowed_x_handles(self) -> List[str]:
        if self.settings.allowed_x_handles:
            return self.settings.allowed_x_handles
        if self.settings.source_mode == "official":
            return self.settings.official_x_handles
        return []

    def _build_prompt(self, now: datetime, start: datetime) -> str:
        language_hints = ", ".join(self.settings.language_hints) if self.settings.language_hints else "ja, en"
        today_label = now.strftime("%Y-%m-%d")
        official_handles = ", ".join(self.settings.official_x_handles) or "主要公式アカウント"
        priority_handles = ", ".join(self.settings.priority_x_handles) or "なし"
        source_mode = self.settings.source_mode
        return f"""
過去{self.settings.hours}時間以内のX上での{self.settings.topic}に関するトレンド、主要な議論、高頻出トピックを検索し、Slack に投稿できる形式の朝刊にまとめてください。

前提:
- 対象期間の目安: {start.isoformat()} から {now.isoformat()}
- x_search の検索範囲: {start.date().isoformat()} から {now.date().isoformat()}
- 優先言語: {language_hints}
- 想定読者: 投資家 + エンジニア
- 文体: 日本語、簡潔、情報密度高め、断定しすぎない
- source_mode: {source_mode}
- 公式アンカーとして特に重視するアカウント: {official_handles}
- 重点観測する非公式アカウント: {priority_handles}

要件:
1. 過去{self.settings.hours}時間以内の内容を優先し、議論量が多く、拡散力が高く、明確なエンゲージメントがある話題を優先する
2. 公式情報は重要な確認ソースとして扱うが、source_mode=official でない限り、公式アカウントだけに偏らず、研究者、起業家、開発者、投資家、OSS作者、主要インフルエンサーなど非公式の高エンゲージメント投稿も拾う
3. 散発的な投稿を列挙せず、近い論点を束ねて 3〜{self.settings.cluster_count} 個の最注目トピックにまとめる
4. 各トピックには以下を含める
   - 明確なタイトル
   - 2〜4件の要点サマリー
   - 「なぜ注目すべきか」を1文で
   - 2〜{self.settings.post_links_per_topic}件の元投稿リンク
5. トピック選定では次を重視する
   - 公式発表や主要人物発言そのもの
   - その話題に対する二次拡散、引用、反論、実装報告、比較検証
   - 同じ論点が複数の独立したアカウントから語られていること
   - 投資や産業構造に波及しそうな示唆
6. 投資・市場シグナルとして、モデル性能だけでなく、価格改定、API/製品リリース、提携、M&A、設備投資、GPU/半導体、クラウド需要、企業導入、規制、著作権、収益化、推論コスト、利用者の乗り換えなども注視する
7. 不確かな情報やゴシップは避ける。未確認情報を扱う場合は未確認と明記し、断定しない
8. 投資助言に見える表現は禁止する。代わりに「どの論点がどの企業群やバリューチェーンに関係しそうか」という観察に留める
9. source_mode ごとの探索姿勢:
   - official: 公式アカウントと主要人物の発信を中心に、確認性を最優先する
   - mixed: 公式を起点にしつつ、界隈でバズっている非公式投稿や実務家の反応を必ず混ぜる
   - discovery: 非公式の高反応投稿や新興論点を広めに探索しつつ、重要な事実は公式ソースで裏取りする
10. 重点観測する非公式アカウントは、source_mode=official 以外では優先的に検索・評価する。ただし公式確認ソースとは扱わず、公式発表の代替にしない
11. 大きなニュースがなくても、最も議論された論点や空気感を埋めて空白を作らない

根拠と引用の厳格ルール:
- 各トピックの主要な事実、数値、企業名、提携、資金調達、価格、製品名、機能名は、そのトピック直下の「元投稿」リンクから読者が直接たどれる範囲だけに限定する
- リンク先投稿に明示されていない記事本文・外部ページ・スレッド続き・引用ポスト由来の詳細を本文に混ぜない。使う場合は、その詳細が確認できる投稿URLも「元投稿」に追加する
- 1つのトピック内で複数ソースを束ねる場合、各要点がどの元投稿から確認できるかを崩さない。元投稿が支えない要点は削除するか「未確認」と明記する
- 「引用元スレッド」「記事では」「報道では」のような表現は、該当する確認可能URLを元投稿に含められる場合だけ使う
- 公式アカウントではない投稿は「反応」「実装報告」「観測」として扱い、公式発表や確定事実の根拠にしない
- 迷った場合は、派手な要約より引用元の正確性を優先して、控えめに書く

出力形式:
- Slack対応のMarkdownを使う
- 各セクションと各テーマに明確なタイトルを付ける
- 投稿リンクは https://... 形式で直接記載する
- 表は使わず、短い箇条書き中心でまとめる
- 全体として「情報密度の高いコミュニティ朝刊」のようにまとめる
- 公式ソースだけでなく、反応の大きかった非公式投稿を最低1件は含める。ただし source_mode=official の場合はこの制約を外す
- 必ず最後に「今日の観察」を 2〜3 点つけ、そのうち1点はソースの偏りや市場との接続に触れる

出力構造:
**🌅 Twitter {self.settings.topic} 朝刊 | {today_label}**

**今日の公式アップデート**
**1. {{トピックタイトル}}**
- 要点1
- 要点2

> なぜ注目すべきか：{{一文サマリー}}

元投稿:
https://x.com/...
https://x.com/...

**界隈でバズっている論点**
**2. {{トピックタイトル}}**
- 要点1
- 要点2
- 要点3

> なぜ注目すべきか：{{一文サマリー}}

元投稿:
https://x.com/...
https://x.com/...

**投資に効きそうなシグナル**
**3. {{トピックタイトル}}**
- 要点1
- 要点2

> なぜ注目すべきか：{{一文サマリー}}

元投稿:
https://x.com/...
https://x.com/...

必要なら **監視継続 / 未確認** セクションを追加してよい

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
