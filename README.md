# x-research

X(Twitter) 上の AI 関連ホットトピックを過去 24 時間ぶん収集し、Slack に「Twitter AI 朝刊」として投稿する定期バッチです。

このリポジトリは次の流れで動きます。

1. X API v2 recent search で広めの AI 系クエリを実行
2. 取得した投稿をスコアリングして重複排除
3. 高頻出フレーズから 3-6 個の話題クラスターを生成
4. Slack 向け Markdown に整形して Incoming Webhook に投稿

## セットアップ

### 1. Python 環境

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. 環境変数

`.env.example` を参考に環境変数を設定してください。

必須:

- `X_BEARER_TOKEN`: X API Bearer Token
- `SLACK_WEBHOOK_URL`: Slack Incoming Webhook URL

任意:

- `XR_TOPIC`: 収集対象テーマ。初期値は `AI`
- `XR_HOURS`: 収集期間。初期値は `24`
- `XR_MAX_RESULTS_PER_QUERY`: クエリごとの取得件数。初期値は `50`
- `XR_CLUSTER_COUNT`: 出力するトピック数。初期値は `4`
- `XR_POST_LINKS_PER_TOPIC`: トピックごとの元投稿リンク数。初期値は `3`
- `XR_LANGUAGE_HINTS`: カンマ区切り。例: `ja,en`
- `XR_EXTRA_QUERIES`: 追加クエリ。改行区切り
- `XR_DRY_RUN`: `true` にすると Slack 送信せず stdout に出力

### 3. ローカル実行

```bash
python -m src.x_research.main
```

または:

```bash
python run.py
```

## GitHub Actions

`.github/workflows/twitter-ai-morning.yml` を使うと、GitHub Actions から定期実行できます。

必要な Repository Secrets:

- `X_BEARER_TOKEN`
- `SLACK_WEBHOOK_URL`

必要に応じて Repository Variables を追加できます。

- `XR_TOPIC`
- `XR_HOURS`
- `XR_CLUSTER_COUNT`
- `XR_MAX_RESULTS_PER_QUERY`
- `XR_LANGUAGE_HINTS`

## 実装メモ

- 収集は X API の recent search を使用します
- クラスタリングは軽量なヒューリスティックです
- LLM 依存を外しているので、まずは安定して定期運用しやすい構成です
- 将来的に OpenAI/xAI などで要約部分だけ差し替えやすいように、整形処理は分離しています
