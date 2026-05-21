# x-research

xAI API の Grok + `x_search` を使って、X 上のホットトピックを調べ、Slack に「Twitter AI 朝刊」として投稿する定期バッチです。

このリポジトリは次の流れで動きます。

1. xAI Responses API に自然言語プロンプトを送る
2. Grok が `x_search` を使って X 上の直近トレンドを調べる
3. Grok が Slack 向け Markdown の朝刊にまとめる
4. Slack Incoming Webhook に投稿する

## セットアップ

### 1. Python 環境

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. 環境変数

`.env.example` を参考に `.env` を作成するか、シェル変数として設定してください。

必須:

- `XAI_API_KEY`: xAI API key
- `SLACK_WEBHOOK_URL`: Slack Incoming Webhook URL

`XR_DRY_RUN=true` の間は `XAI_API_KEY` が未設定でも動かせます。モックの朝刊を生成して、Slack 連携や定期実行だけ確認できます。

任意:

- `XR_TOPIC`: 収集対象テーマ。初期値は `AI`
- `XR_HOURS`: 収集期間。初期値は `24`
- `XR_CLUSTER_COUNT`: 出力するトピック数の目安。初期値は `3`
- `XR_POST_LINKS_PER_TOPIC`: トピックごとの元投稿リンク数の目安。初期値は `2`
- `XR_LANGUAGE_HINTS`: カンマ区切り。例: `ja,en`
- `XR_SOURCE_MODE`: 収集方針。`official` / `mixed` / `discovery`。初期値は `mixed`
- `XR_OFFICIAL_X_HANDLES`: 公式アンカーとして重視する handles。初期値は `OpenAI,AnthropicAI,GoogleDeepMind,xAI,GoogleAI`
- `XR_MODEL`: xAI で使うモデル。初期値は `grok-4.3`
- `XR_MAX_TURNS`: Grok がツール利用しながら応答を完成させる最大ターン数。初期値は `2`
- `XR_ALLOWED_X_HANDLES`: 収集対象をハードに絞るときの allowed handles。初期値は空
- `XR_EXCLUDED_X_HANDLES`: 除外したい handles。カンマ区切り
- `XR_DRY_RUN`: 初期値は `false`。`true` にすると xAI API と `x_search` を呼ばず、モックの朝刊を生成して Slack 投稿まで確認する

### 3. ローカル実行

まずは `.env` の既定値で本番実行できます。必要なら dry-run に切り替えてモック確認もできます。

```bash
cp .env.example .env
```

`.env` を埋めたら、そのまま本番実行:

```bash
python run.py
```

モック実行で Slack 連携だけ確認したい場合:

```bash
XR_DRY_RUN=true python run.py
```

## GitHub Actions

`.github/workflows/twitter-ai-morning.yml` を使うと、GitHub Actions から毎日 `22:00 JST` に定期実行できます。

必要な Repository Secrets:

- `XAI_API_KEY`
- `SLACK_WEBHOOK_URL`

必要に応じて Repository Variables を追加できます。

- `XR_TOPIC`
- `XR_HOURS`
- `XR_CLUSTER_COUNT`
- `XR_POST_LINKS_PER_TOPIC`
- `XR_LANGUAGE_HINTS`
- `XR_SOURCE_MODE`
- `XR_OFFICIAL_X_HANDLES`
- `XR_MODEL`
- `XR_MAX_TURNS`
- `XR_ALLOWED_X_HANDLES`
- `XR_EXCLUDED_X_HANDLES`
- `XR_DRY_RUN`

## コストメモ

- 課金は `x_search` の call 数と、使う Grok モデルの token usage に依存します
- `XR_DRY_RUN=true` は APIモック実行なので、xAI API や `x_search` の課金は発生しません
- `XR_ALLOWED_X_HANDLES` で対象を絞ると、探索範囲とコストのコントロールに役立ちます
- `XR_SOURCE_MODE=mixed` では公式情報を重視しつつ、非公式の高エンゲージメント投稿や市場シグナルも拾いやすくなります

## おすすめ運用

- まずは `XR_SOURCE_MODE=mixed` を既定にして、公式とコミュニティの両方を観測する
- 公式発表だけを確実に追いたい日は `XR_SOURCE_MODE=official`
- 新しい論点や界隈の空気感を広めに拾いたい日は `XR_SOURCE_MODE=discovery`
- `XR_ALLOWED_X_HANDLES` は常用せず、特定テーマの深掘り時だけ使う
