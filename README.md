# aws-hands-on
AWS DVA / SAA ハンズオン学習の記録

# Week 01 - Lambda 基礎 & S3 イベントトリガー

## 🎯 ゴール
- Lambda 関数をゼロから作成し、環境変数と CloudWatch Logs の仕組みを体験する
- S3 イベントトリガーで画像アップロード時に Lambda が自動実行される仕組みを構築する

---

## ハンズオン① Lambda 関数の作成と基本操作

### Step 1: Lambda 関数を作成する

1. AWS Console → **Lambda** → 「関数の作成」
2. 以下のように設定する

| 項目 | 設定値 |
|------|--------|
| 作成方法 | 一から作成 |
| 関数名 | `dva-week01-hello` |
| ランタイム | Python 3.12 |
| アーキテクチャ | x86_64 |
| 実行ロール | 基本的な Lambda アクセス権限で新しいロールを作成 |

3. 「関数の作成」をクリック

### Step 2: 関数コードを書く

コードエディタに以下を貼り付けて「Deploy」をクリック。

```python
import json
import os
import logging

# ロガーの設定
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    # 環境変数を取得
    env_name = os.environ.get('ENV_NAME', 'unknown')
    app_version = os.environ.get('APP_VERSION', '0.0.0')

    # ログ出力（CloudWatch Logs に記録される）
    logger.info(f"関数が実行されました - 環境: {env_name}, バージョン: {app_version}")
    logger.info(f"受信イベント: {json.dumps(event, ensure_ascii=False)}")

    # コンテキスト情報をログに出力
    logger.info(f"関数名: {context.function_name}")
    logger.info(f"メモリ割り当て: {context.memory_limit_in_mb}MB")
    logger.info(f"残り実行時間: {context.get_remaining_time_in_millis()}ms")
    logger.info(f"リクエストID: {context.aws_request_id}")

    return {
        'statusCode': 200,
        'body': json.dumps({
            'message': f'Hello from {env_name}!',
            'version': app_version,
            'function_name': context.function_name,
            'request_id': context.aws_request_id
        }, ensure_ascii=False)
    }
```

### Step 3: 環境変数を設定する

1. 「設定」タブ → 「環境変数」 → 「編集」
2. 以下の 2 つを追加する

| キー | 値 |
|------|-----|
| `ENV_NAME` | `development` |
| `APP_VERSION` | `1.0.0` |

3. 「保存」をクリック

> **DVA 試験ポイント**: 環境変数は Lambda の設定で管理し、コードに直接書かない。
> 機密情報は KMS で暗号化できる（デフォルトで AWS 管理キーが使われる）。

### Step 4: テストイベントで実行する

1. 「テスト」タブ → テストイベントを新規作成
2. イベント名: `test-event`
3. イベント JSON:

```json
{
  "name": "DVA学習者",
  "action": "ハンズオン実行中"
}
```

4. 「テスト」をクリック → 実行結果を確認

### Step 5: CloudWatch Logs を確認する

1. 「モニタリング」タブ → 「CloudWatch Logs を表示」をクリック
2. 最新のログストリームを開く
3. 以下の内容がログに記録されていることを確認する
   - `関数が実行されました - 環境: development, バージョン: 1.0.0`
   - `受信イベント: {"name": "DVA学習者", ...}`
   - 関数名、メモリ割り当て、残り実行時間、リクエストID

> **DVA 試験ポイント**: Lambda のログは自動的に CloudWatch Logs に送信される。
> ロググループ名は `/aws/lambda/関数名` の形式。
> 実行ロールに `logs:CreateLogGroup`, `logs:CreateLogStream`, `logs:PutLogEvents` の権限が必要。

### Step 6: 環境変数を変えて再実行してみる

1. 「設定」→「環境変数」→ `ENV_NAME` を `production` に変更
2. もう一度テスト実行 → レスポンスの `message` が変わることを確認

> **気づきメモ**: コードを変更せずに、環境変数だけで動作を切り替えられる。
> 本番環境と開発環境の設定の切り替えに使われるパターン。

---

## ハンズオン② Lambda + S3 イベントトリガー

### 構成図

```
┌──────────┐    画像を       ┌──────────────┐    自動       ┌──────────────────┐
│          │  アップロード   │              │   トリガー   │                  │
│   あなた  │ ──────────────→│   S3 Bucket  │ ──────────→  │  Lambda 関数      │
│          │                │              │              │ （画像情報をログ） │
└──────────┘                └──────────────┘              └──────────────────┘
                                                                  │
                                                                  ↓
                                                         ┌──────────────────┐
                                                         │  CloudWatch Logs │
                                                         │ （処理結果を記録）│
                                                         └──────────────────┘
```

### Step 1: S3 バケットを作成する

1. AWS Console → **S3** → 「バケットを作成」
2. 以下のように設定する

| 項目 | 設定値 |
|------|--------|
| バケット名 | `dva-week01-images-あなたの名前`（グローバルで一意にする） |
| リージョン | Lambda と同じリージョン（ap-northeast-1 推奨） |
| その他 | すべてデフォルトのまま |

3. 「バケットを作成」をクリック

### Step 2: Lambda 関数を作成する

1. Lambda → 「関数の作成」
2. 設定:

| 項目 | 設定値 |
|------|--------|
| 関数名 | `dva-week01-s3-trigger` |
| ランタイム | Python 3.12 |
| 実行ロール | 基本的な Lambda アクセス権限で新しいロールを作成 |

3. 関数コード:

```python
import json
import logging
import urllib.parse

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    logger.info(f"受信イベント: {json.dumps(event, ensure_ascii=False)}")

    # S3 イベントからファイル情報を取得
    for record in event['Records']:
        # バケット情報
        bucket_name = record['s3']['bucket']['name']

        # オブジェクトキー（ファイル名）を URL デコード
        object_key = urllib.parse.unquote_plus(
            record['s3']['object']['key']
        )

        # ファイルサイズ
        file_size = record['s3']['object']['size']

        # イベントタイプ
        event_name = record['eventName']

        # ログに記録
        logger.info("=" * 50)
        logger.info(f"イベント種別: {event_name}")
        logger.info(f"バケット名:   {bucket_name}")
        logger.info(f"ファイル名:   {object_key}")
        logger.info(f"ファイルサイズ: {file_size} bytes ({file_size / 1024:.1f} KB)")
        logger.info("=" * 50)

        # 画像ファイルかどうかを判定
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
        is_image = any(object_key.lower().endswith(ext) for ext in image_extensions)

        if is_image:
            logger.info(f"画像ファイルを検出: {object_key}")
            # ここに画像処理のロジックを追加できる
            # 例: サムネイル生成、メタデータ抽出など
        else:
            logger.info(f"画像以外のファイル: {object_key}")

    return {
        'statusCode': 200,
        'body': json.dumps({
            'message': 'S3 イベントを正常に処理しました',
            'processed_records': len(event['Records'])
        }, ensure_ascii=False)
    }
```

4. 「Deploy」をクリック

### Step 3: Lambda に S3 読み取り権限を追加する

1. Lambda の「設定」タブ → 「アクセス権限」
2. 実行ロール名をクリック → IAM コンソールが開く
3. 「許可を追加」→「ポリシーをアタッチ」
4. `AmazonS3ReadOnlyAccess` を検索してアタッチ

> **DVA 試験ポイント**: Lambda の実行ロール（Execution Role）は、
> Lambda が他の AWS サービスにアクセスするための IAM ロール。
> S3 からオブジェクトを読み取るには `s3:GetObject` 権限が必要。

### Step 4: S3 イベントトリガーを設定する

1. Lambda 関数の画面に戻る →「トリガーを追加」
2. 以下のように設定する

| 項目 | 設定値 |
|------|--------|
| ソース | S3 |
| バケット | `dva-week01-images-あなたの名前` |
| イベントタイプ | すべてのオブジェクト作成イベント (s3:ObjectCreated:*) |
| プレフィックス | `uploads/`（この配下のファイルだけトリガー） |
| サフィックス | 空欄のまま |

3. 再帰呼び出しの警告チェックボックスにチェック → 「追加」

> **DVA 試験ポイント**: S3 イベント通知のイベントタイプには
> `s3:ObjectCreated:*`, `s3:ObjectRemoved:*`, `s3:ObjectRestore:*` などがある。
> プレフィックス / サフィックスでフィルタリングできる。

### Step 5: 画像をアップロードしてテストする

1. S3 コンソールで作成したバケットを開く
2. 「フォルダの作成」→ `uploads` フォルダを作成
3. `uploads/` フォルダの中に適当な画像ファイルをアップロード
4. Lambda →「モニタリング」→「CloudWatch Logs を表示」
5. 最新のログストリームを確認する

以下のようなログが表示されていれば成功:

```
イベント種別: ObjectCreated:Put
バケット名:   dva-week01-images-あなたの名前
ファイル名:   uploads/test-image.jpg
ファイルサイズ: 245760 bytes (240.0 KB)
画像ファイルを検出: uploads/test-image.jpg
```

### Step 6: いろいろ試してみる

以下を試して、ログの変化を観察してみてください。

- `uploads/` 以外の場所にファイルをアップロード → Lambda はトリガーされない
- `.txt` ファイルをアップロード → 「画像以外のファイル」とログに出る
- 複数ファイルを一度にアップロード → `Records` 配列に複数レコードが入る

---

## 後片付け（リソース削除）

ハンズオンが終わったら、不要な課金を防ぐためにリソースを削除してください。

```
1. S3 バケット内のオブジェクトをすべて削除 → バケット自体を削除
2. Lambda 関数を 2 つ（dva-week01-hello, dva-week01-s3-trigger）削除
3. IAM ロール（Lambda 作成時に自動生成されたもの）を削除
4. CloudWatch Logs のロググループを削除
```

> **注意**: S3 バケットはオブジェクトが入っていると削除できません。
> 先に「バケットを空にする」を実行してから削除してください。

---

## 学んだこと（振り返り用）

ここに自分の言葉で学びを記録してください。

- Lambda の基本的な構造（ハンドラ、event、context）
- 環境変数でコードを変更せず設定を切り替える方法
- CloudWatch Logs への自動ログ出力の仕組み
- S3 イベント通知 → Lambda のイベント駆動アーキテクチャ
- Lambda 実行ロールの権限管理
- S3 イベントのプレフィックス / サフィックスフィルタリング

## つまずいたところ

（ここに自分が詰まった点と解決方法を記録してください）

---

## DVA 試験で問われるポイントまとめ

| テーマ | 覚えること |
|--------|-----------|
| Lambda ハンドラ | `lambda_handler(event, context)` が基本形。event にトリガー情報、context にランタイム情報が入る |
| 環境変数 | `os.environ` で取得。機密情報は KMS で暗号化可能 |
| CloudWatch Logs | ロググループは `/aws/lambda/関数名`。実行ロールに Logs 権限が必要 |
| S3 イベント | `s3:ObjectCreated:*` などのイベントタイプでトリガー |
| 実行ロール | Lambda が他サービスにアクセスするための IAM ロール。最小権限の原則で設定 |
| 同時実行数 | デフォルト 1,000（リージョンあたり）。予約済み同時実行数で制御可能 |