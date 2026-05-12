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

# Week 02 - API Gateway + Lambda + DynamoDB（サーバーレス三銃士）

## 🎯 ゴール
- API Gateway + Lambda + DynamoDB で REST API（CRUD）を構築する
- DynamoDB Streams + Lambda でデータ変更時の自動処理を体験する
- DVA 頻出の「サーバーレスアーキテクチャ」を手を動かして理解する

---

## 全体構成図

```
                          ┌─────────────────────────────────────────┐
                          │          API Gateway (REST API)         │
                          │                                         │
                          │  GET    /items      → 全件取得          │
                          │  GET    /items/{id} → 1件取得           │
                          │  POST   /items      → 新規作成          │
                          │  PUT    /items/{id} → 更新              │
                          │  DELETE /items/{id} → 削除              │
                          └──────────┬──────────────────────────────┘
                                     │ 各メソッドが Lambda を呼び出し
                                     ▼
                          ┌─────────────────────┐
                          │    Lambda 関数       │
                          │  (items_handler.py)  │
                          └──────────┬──────────┘
                                     │ boto3 で読み書き
                                     ▼
                          ┌─────────────────────┐
                          │     DynamoDB         │
                          │  テーブル: Items      │
                          │  PK: id (String)     │
                          └──────────┬──────────┘
                                     │ Streams（変更データキャプチャ）
                                     ▼
                          ┌─────────────────────┐
                          │    Lambda 関数       │
                          │ (stream_handler.py)  │
                          │  → 変更ログを記録    │
                          └─────────────────────┘
```

---

## ハンズオン① DynamoDB テーブルの作成

### Step 1: テーブルを作成する

1. AWS Console → **DynamoDB** → 「テーブルの作成」
2. 以下のように設定する

| 項目 | 設定値 |
|------|--------|
| テーブル名 | `dva-items` |
| パーティションキー | `id`（文字列） |
| ソートキー | なし |
| テーブル設定 | 設定をカスタマイズ |
| キャパシティモード | オンデマンド |

3. タグを追加

| Key | Value |
|-----|-------|
| `aws-hands-on` | `02` |

4. 「テーブルの作成」をクリック

> **DVA 試験ポイント**: オンデマンドモードはキャパシティの事前設定が不要。
> プロビジョンドモードは予測可能なワークロード向けで、Auto Scaling と組み合わせる。
> DVA ではどちらを選ぶべきかのシナリオ問題が出る。

---

## ハンズオン② Lambda 関数（CRUD 処理）の作成

### Step 1: IAM ロールを先に作成する

Lambda が DynamoDB にアクセスするためのロールを作成します。

1. AWS Console → **IAM** → 「ロール」 → 「ロールを作成」
2. 信頼されたエンティティ: **AWS のサービス** → **Lambda**
3. ポリシーをアタッチ:
   - `AmazonDynamoDBFullAccess`
   - `AWSLambdaBasicExecutionRole`
4. ロール名: `dva-week02-lambda-dynamodb-role`
5. タグ: `aws-hands-on` = `02`
6. 「ロールを作成」

### Step 2: Lambda 関数を作成する

1. Lambda → 「関数の作成」

| 項目 | 設定値 |
|------|--------|
| 関数名 | `dva-week02-items-api` |
| ランタイム | Python 3.12 |
| 実行ロール | 既存のロールを使用 → `dva-week02-lambda-dynamodb-role` |

2. タグ: `aws-hands-on` = `02`

### Step 3: 関数コードを貼り付ける

以下のコード（`items_handler.py` と同じ内容）を Lambda のコードエディタに貼り付けて「Deploy」。

```python
import json
import boto3
import uuid
import logging
from decimal import Decimal

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('dva-items')


class DecimalEncoder(json.JSONEncoder):
    """DynamoDB の Decimal 型を JSON に変換するためのエンコーダー"""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return int(obj) if obj % 1 == 0 else float(obj)
        return super().default(obj)


def response(status_code, body):
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps(body, cls=DecimalEncoder, ensure_ascii=False)
    }


def lambda_handler(event, context):
    logger.info(f"受信イベント: {json.dumps(event, ensure_ascii=False)}")

    http_method = event.get('httpMethod', '')
    path = event.get('path', '')
    path_params = event.get('pathParameters') or {}
    body = event.get('body')

    try:
        # GET /items - 全件取得
        if http_method == 'GET' and path == '/items':
            result = table.scan()
            return response(200, {
                'items': result['Items'],
                'count': result['Count']
            })

        # GET /items/{id} - 1件取得
        elif http_method == 'GET' and 'id' in path_params:
            item_id = path_params['id']
            result = table.get_item(Key={'id': item_id})

            if 'Item' not in result:
                return response(404, {'error': f'Item {item_id} が見つかりません'})

            return response(200, result['Item'])

        # POST /items - 新規作成
        elif http_method == 'POST':
            if body is None:
                return response(400, {'error': 'リクエストボディが空です'})

            item_data = json.loads(body)
            item_id = str(uuid.uuid4())[:8]

            item = {
                'id': item_id,
                'name': item_data.get('name', ''),
                'description': item_data.get('description', ''),
                'price': item_data.get('price', 0),
                'status': 'active'
            }

            table.put_item(Item=item)
            logger.info(f"アイテム作成: {item_id}")

            return response(201, {
                'message': 'アイテムを作成しました',
                'item': item
            })

        # PUT /items/{id} - 更新
        elif http_method == 'PUT' and 'id' in path_params:
            item_id = path_params['id']

            if body is None:
                return response(400, {'error': 'リクエストボディが空です'})

            item_data = json.loads(body)

            # まず存在確認
            existing = table.get_item(Key={'id': item_id})
            if 'Item' not in existing:
                return response(404, {'error': f'Item {item_id} が見つかりません'})

            # UpdateExpression を動的に構築
            update_parts = []
            expression_values = {}
            expression_names = {}

            for key, value in item_data.items():
                if key == 'id':
                    continue  # パーティションキーは更新不可
                placeholder = f":val_{key}"
                name_placeholder = f"#attr_{key}"
                update_parts.append(f"{name_placeholder} = {placeholder}")
                expression_values[placeholder] = value
                expression_names[name_placeholder] = key

            if not update_parts:
                return response(400, {'error': '更新するフィールドがありません'})

            result = table.update_item(
                Key={'id': item_id},
                UpdateExpression='SET ' + ', '.join(update_parts),
                ExpressionAttributeValues=expression_values,
                ExpressionAttributeNames=expression_names,
                ReturnValues='ALL_NEW'
            )

            logger.info(f"アイテム更新: {item_id}")

            return response(200, {
                'message': 'アイテムを更新しました',
                'item': result['Attributes']
            })

        # DELETE /items/{id} - 削除
        elif http_method == 'DELETE' and 'id' in path_params:
            item_id = path_params['id']

            # 存在確認
            existing = table.get_item(Key={'id': item_id})
            if 'Item' not in existing:
                return response(404, {'error': f'Item {item_id} が見つかりません'})

            table.delete_item(Key={'id': item_id})
            logger.info(f"アイテム削除: {item_id}")

            return response(200, {'message': f'アイテム {item_id} を削除しました'})

        else:
            return response(400, {'error': f'未対応のリクエスト: {http_method} {path}'})

    except Exception as e:
        logger.error(f"エラー発生: {str(e)}")
        return response(500, {'error': '内部エラーが発生しました'})
```

### Step 4: テスト実行（POST → GET で確認）

1. 「テスト」タブ → テストイベントを作成

**テスト①: アイテム作成（POST）**

イベント名: `create-item`
```json
{
  "httpMethod": "POST",
  "path": "/items",
  "pathParameters": null,
  "body": "{\"name\": \"AWS教科書\", \"description\": \"DVA対策本\", \"price\": 3500}"
}
```

実行 → `statusCode: 201` とレスポンスの `id` を確認（例: `a1b2c3d4`）

**テスト②: 全件取得（GET）**

イベント名: `get-all-items`
```json
{
  "httpMethod": "GET",
  "path": "/items",
  "pathParameters": null,
  "body": null
}
```

実行 → 先ほど作成したアイテムが返ってくることを確認

**テスト③: 1件取得（GET by ID）**

イベント名: `get-one-item`（id は作成時のレスポンスから取得）
```json
{
  "httpMethod": "GET",
  "path": "/items/ここにIDを入れる",
  "pathParameters": { "id": "ここにIDを入れる" },
  "body": null
}
```

**テスト④: 更新（PUT）**

イベント名: `update-item`
```json
{
  "httpMethod": "PUT",
  "path": "/items/ここにIDを入れる",
  "pathParameters": { "id": "ここにIDを入れる" },
  "body": "{\"price\": 2980, \"status\": \"on_sale\"}"
}
```

**テスト⑤: 削除（DELETE）**

イベント名: `delete-item`
```json
{
  "httpMethod": "DELETE",
  "path": "/items/ここにIDを入れる",
  "pathParameters": { "id": "ここにIDを入れる" },
  "body": null
}
```

> **DVA 試験ポイント**:
> - `put_item` は既存アイテムがあれば上書き。条件付き書き込みには `ConditionExpression` を使う
> - `update_item` は `UpdateExpression` で部分更新。`SET`, `REMOVE`, `ADD`, `DELETE` の4つのアクション
> - `get_item` は結果整合性がデフォルト。強い整合性には `ConsistentRead=True` を指定

---

## ハンズオン③ API Gateway でエンドポイントを作成

### Step 1: REST API を作成する

1. AWS Console → **API Gateway** → 「REST API」→「構築」

| 項目 | 設定値 |
|------|--------|
| プロトコル | REST |
| 新しいAPIの作成 | 新しい API |
| API名 | `dva-week02-items-api` |
| エンドポイントタイプ | リージョン |

2. 「APIの作成」をクリック

### Step 2: リソースとメソッドを作成する

**/items リソースの作成**

1. 「リソースの作成」をクリック
2. リソースパス: `/`、リソース名: `items`
3. 「CORS (Cross Origin Resource Sharing)」にチェック
4. 「リソースの作成」

**/items/{id} リソースの作成**

1. `/items` を選択した状態で「リソースの作成」
2. リソースパス: `/items`、リソース名: `{id}`
3. 「CORS」にチェック
4. 「リソースの作成」

### Step 3: メソッドを追加する

**/items に GET と POST を追加**

1. `/items` を選択 → 「メソッドの作成」
2. メソッド: `GET`
3. 統合タイプ: Lambda 関数
4. Lambda プロキシ統合: **チェックを入れる**（重要）
5. Lambda 関数: `dva-week02-items-api`
6. 同様に `POST` メソッドも追加

**/items/{id} に GET, PUT, DELETE を追加**

1. `/items/{id}` を選択 → 各メソッドを追加
2. すべて Lambda プロキシ統合にチェック
3. Lambda 関数: `dva-week02-items-api`

> **DVA 試験ポイント**: Lambda プロキシ統合を有効にすると、
> API Gateway はリクエスト全体（ヘッダー、パス、クエリパラメータ、ボディ）を
> そのまま Lambda の event オブジェクトに渡す。マッピングテンプレートの設定が不要になる。

### Step 4: API をデプロイする

1. 「APIのデプロイ」をクリック
2. ステージ: 新しいステージ → ステージ名: `dev`
3. 「デプロイ」

デプロイ後に表示される **呼び出し URL** をコピーする。
（例: `https://xxxxxxxx.execute-api.ap-northeast-1.amazonaws.com/dev`）

### Step 5: curl または PowerShell でテストする

PowerShell の場合、`curl` の代わりに `Invoke-RestMethod` を使います。

```powershell
# 変数に URL をセット（自分の URL に置き換えてください）
$API = "https://xxxxxxxx.execute-api.ap-northeast-1.amazonaws.com/dev"

# POST: アイテム作成
Invoke-RestMethod -Method POST -Uri "$API/items" `
  -ContentType "application/json" `
  -Body '{"name": "Lambda入門書", "description": "サーバーレス学習用", "price": 2800}'

# GET: 全件取得
Invoke-RestMethod -Method GET -Uri "$API/items"

# GET: 1件取得（id は POST のレスポンスから取得）
Invoke-RestMethod -Method GET -Uri "$API/items/ここにIDを入れる"

# PUT: 更新
Invoke-RestMethod -Method PUT -Uri "$API/items/ここにIDを入れる" `
  -ContentType "application/json" `
  -Body '{"price": 1980}'

# DELETE: 削除
Invoke-RestMethod -Method DELETE -Uri "$API/items/ここにIDを入れる"
```

ブラウザから `https://xxxxxxxx.execute-api.ap-northeast-1.amazonaws.com/dev/items` にアクセスしても GET の結果が見えます。

> **DVA 試験ポイント**:
> - ステージ（dev / staging / prod）ごとに異なるステージ変数を設定できる
> - スロットリング: デフォルトでリージョンあたり 10,000 リクエスト/秒
> - API キーと使用量プランでアクセス制御・レート制限が可能

---

## ハンズオン④ DynamoDB Streams + Lambda

### 構成図

```
┌────────────┐  PUT/DELETE   ┌────────────┐   Stream    ┌────────────────────┐
│ items API  │ ───────────→  │  DynamoDB   │ ─────────→ │  Lambda            │
│ (既存)     │               │  dva-items  │            │  stream_handler    │
└────────────┘               └────────────┘            │  → 変更内容をログ  │
                                                        └────────────────────┘
```

### Step 1: DynamoDB Streams を有効にする

1. DynamoDB → テーブル `dva-items` → 「エクスポートおよびストリーム」タブ
2. 「DynamoDB ストリームの詳細」→ 「有効にする」
3. 表示タイプ: **新しいイメージと古いイメージ**（`NEW_AND_OLD_IMAGES`）
4. 「ストリームを有効にする」

> **DVA 試験ポイント**: ストリームの表示タイプは4種類:
> - `KEYS_ONLY` — 変更されたアイテムのキーのみ
> - `NEW_IMAGE` — 変更後のアイテム全体
> - `OLD_IMAGE` — 変更前のアイテム全体
> - `NEW_AND_OLD_IMAGES` — 変更前後の両方（差分検出に最適）

### Step 2: Stream 処理用の Lambda を作成する

1. Lambda → 「関数の作成」

| 項目 | 設定値 |
|------|--------|
| 関数名 | `dva-week02-stream-handler` |
| ランタイム | Python 3.12 |
| 実行ロール | 既存のロール → `dva-week02-lambda-dynamodb-role` |

2. タグ: `aws-hands-on` = `02`

### Step 3: Stream 処理用の IAM 権限を追加

1. IAM → ロール `dva-week02-lambda-dynamodb-role` を開く
2. 「許可を追加」→「ポリシーをアタッチ」
3. `AWSLambdaDynamoDBExecutionRole` を検索してアタッチ

> この権限で `dynamodb:GetRecords`, `dynamodb:GetShardIterator`,
> `dynamodb:DescribeStream`, `dynamodb:ListStreams` が付与される。

### Step 4: 関数コードを貼り付ける

```python
import json
import logging
from datetime import datetime

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    logger.info(f"Streams レコード数: {len(event['Records'])}")

    for record in event['Records']:
        # イベント情報
        event_name = record['eventName']       # INSERT, MODIFY, REMOVE
        event_id = record['eventID']
        timestamp = record['dynamodb'].get('ApproximateCreationDateTime', 0)
        event_time = datetime.fromtimestamp(timestamp).isoformat()

        logger.info("=" * 60)
        logger.info(f"イベント種別:   {event_name}")
        logger.info(f"イベントID:     {event_id}")
        logger.info(f"発生時刻:       {event_time}")

        # 変更内容の解析
        if event_name == 'INSERT':
            new_item = record['dynamodb']['NewImage']
            item_id = new_item['id']['S']
            item_name = new_item.get('name', {}).get('S', '(名前なし)')
            logger.info(f"[新規作成] id={item_id}, name={item_name}")
            logger.info(f"  作成データ: {json.dumps(new_item, ensure_ascii=False)}")

        elif event_name == 'MODIFY':
            old_item = record['dynamodb']['OldImage']
            new_item = record['dynamodb']['NewImage']
            item_id = new_item['id']['S']
            logger.info(f"[更新] id={item_id}")

            # 変更されたフィールドを検出
            all_keys = set(list(old_item.keys()) + list(new_item.keys()))
            for key in all_keys:
                old_val = old_item.get(key)
                new_val = new_item.get(key)
                if old_val != new_val:
                    logger.info(f"  変更フィールド: {key}")
                    logger.info(f"    変更前: {old_val}")
                    logger.info(f"    変更後: {new_val}")

        elif event_name == 'REMOVE':
            old_item = record['dynamodb']['OldImage']
            item_id = old_item['id']['S']
            item_name = old_item.get('name', {}).get('S', '(名前なし)')
            logger.info(f"[削除] id={item_id}, name={item_name}")
            logger.info(f"  削除データ: {json.dumps(old_item, ensure_ascii=False)}")

        logger.info("=" * 60)

    return {
        'statusCode': 200,
        'body': json.dumps({
            'message': f'{len(event["Records"])} 件の変更を処理しました'
        })
    }
```

「Deploy」をクリック。

### Step 5: DynamoDB Streams をトリガーに設定する

1. Lambda 関数 `dva-week02-stream-handler` →「トリガーを追加」
2. ソース: **DynamoDB**
3. テーブル: `dva-items`
4. バッチサイズ: `10`
5. 開始位置: **最新（Trim horizon ではなく Latest）**
6. 「追加」をクリック

> **DVA 試験ポイント**:
> - `Trim horizon`: ストリーム内の最も古いレコードから処理開始
> - `Latest`: 追加された新しいレコードのみ処理（通常はこちら）
> - バッチサイズ: 1回の Lambda 呼び出しで処理するレコードの最大数

### Step 6: 動作テスト

先ほど作成した API を使って、データを操作してみます。

```powershell
# 1. アイテム作成 → INSERT イベントが発生
Invoke-RestMethod -Method POST -Uri "$API/items" `
  -ContentType "application/json" `
  -Body '{"name": "Streams テスト", "description": "DynamoDB Streams の動作確認", "price": 0}'

# 2. アイテム更新 → MODIFY イベントが発生（id は上のレスポンスから取得）
Invoke-RestMethod -Method PUT -Uri "$API/items/ここにIDを入れる" `
  -ContentType "application/json" `
  -Body '{"price": 1000, "name": "Streams テスト（更新済み）"}'

# 3. アイテム削除 → REMOVE イベントが発生
Invoke-RestMethod -Method DELETE -Uri "$API/items/ここにIDを入れる"
```

`dva-week02-stream-handler` の CloudWatch Logs を確認して、INSERT / MODIFY / REMOVE それぞれのイベントがログに記録されていれば成功です。

---

## 後片付け

タグベースの一括削除スクリプト（Week 01 で作成済み）を使います。

```powershell
python common/scripts/cleanup_by_tag.py --value 02 --dry-run   # まず確認
python common/scripts/cleanup_by_tag.py --value 02             # 削除実行
```

手動で削除する場合の順序:
```
1. API Gateway の REST API を削除
2. Lambda 関数を 2 つ削除（items-api, stream-handler）
3. DynamoDB テーブルを削除（Streams も自動削除される）
4. IAM ロールを削除
5. CloudWatch Logs のロググループを削除
```

---

## 学んだこと（振り返り用）

（ハンズオン後に自分の言葉で記入してください）

- API Gateway の Lambda プロキシ統合の仕組み
- REST API のリソースとメソッドの関係
- DynamoDB の CRUD 操作（put_item / get_item / update_item / delete_item）
- UpdateExpression の書き方（SET / REMOVE / ADD / DELETE）
- DynamoDB Streams の4つの表示タイプ
- イベント駆動の非同期処理パターン

## つまずいたところ

（ここに自分が詰まった点と解決方法を記録してください）

---

## DVA 試験で問われるポイントまとめ

| テーマ | 覚えること |
|--------|-----------|
| Lambda プロキシ統合 | API Gateway がリクエスト全体を event に渡す。レスポンスは statusCode + headers + body の形式で返す必要がある |
| API Gateway ステージ | dev / prod などの環境をステージで分離。ステージ変数で Lambda のエイリアスを切り替えられる |
| API Gateway 認可 | IAM認可、Cognitoオーソライザー、Lambda オーソライザーの3種類 |
| DynamoDB 整合性 | デフォルトは結果整合性。`ConsistentRead=True` で強い整合性（コスト2倍） |
| DynamoDB Streams | 変更データキャプチャ。24時間保持。Lambda のイベントソースマッピングで処理 |
| Streams 表示タイプ | KEYS_ONLY / NEW_IMAGE / OLD_IMAGE / NEW_AND_OLD_IMAGES |
| UpdateExpression | SET（追加・更新）, REMOVE（属性削除）, ADD（数値加算・セット追加）, DELETE（セットから削除） |
| エラーハンドリング | Streams 処理の Lambda が失敗するとデフォルトでリトライし続ける。bisect-on-error で障害レコードを分離可能 |
# DVA Lambda ハンズオン — Week 2.5 + Week 3

DVA問題集で頻出の「SAM・キャッシュ・バージョン管理・レイヤー・非同期/DLQ」を全て手で動かして体得する。

---

## 全体マップ

### Week 2.5: Lambda 追加ハンズオン（5日間）

| Day | テーマ | 対応するDVA問題パターン |
|-----|--------|------------------------|
| 1 | SAMで天気予報API構築（DVA-10直結） | 外部API呼び出し + APIGWキャッシュ |
| 2 | バージョン・エイリアス・カナリアデプロイ | Blue/Green、トラフィックシフト |
| 3 | Lambdaレイヤー + 環境変数 + Secrets Manager | 設定管理・シークレット注入 |
| 4 | 非同期呼び出し + DLQ + イベントソースマッピング | SQS/SNS統合・エラー処理 |
| 5 | プロビジョンド同時実行 + X-Ray + CloudWatch | コールドスタート対策・監視 |

### Week 3: DynamoDB + Step Functions + CI/CD（7日間）

| Day | テーマ | 主要サービス |
|-----|--------|-------------|
| 1 | DynamoDB基礎 + キー設計 | DynamoDB, GSI, LSI |
| 2 | DynamoDB Streams + TTL + トランザクション | Streams, DAX |
| 3 | Step Functionsで複数Lambdaを連携 | Standard/Express, Map/Choice |
| 4 | CodeCommit + CodeBuild | buildspec.yml |
| 5 | CodeDeploy + CodePipeline（Lambda CI/CD） | appspec.yml, トラフィックシフト |
| 6 | Cognito + API Gateway認証 | User Pool, Authorizer |
| 7 | 模擬試験 + 誤答ノート整備 | TutorialsDojo |

---

# Week 2.5 — Lambda 追加ハンズオン

---

## Day 1: SAMで天気予報PoCを構築【DVA-10直結】

### ゴール

画像のDVA-10と同じ構成を自分で作る。「サーバーレス + APIGW Cache」がなぜ最適解かを体感する。

### 構成図

```
Client → API Gateway (Cache 5min) → Lambda → 外部天気API (Open-Meteo)
                ↓
         CloudWatch Logs / X-Ray
```

### Step 1: SAMプロジェクト作成

```bash
sam init \
  --runtime python3.13 \
  --name weather-poc \
  --app-template hello-world \
  --package-type Zip

cd weather-poc
```

対話式の質問への回答:

| 質問 | 回答 |
|------|------|
| X-Ray tracing | `y` |
| CloudWatch Application Insights | `n` |
| Structured Logging in JSON format | `y` |

### Step 2: Lambda関数を実装

`hello_world/app.py` を以下に置き換える:

```bash
cat > hello_world/app.py << 'EOF'
import json
import urllib.request

def lambda_handler(event, context):
    qs = event.get("queryStringParameters") or {}
    lat = qs.get("lat", "35.86")
    lon = qs.get("lon", "139.65")
    
    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}&current_weather=true"
    )
    
    with urllib.request.urlopen(url, timeout=5) as res:
        data = json.loads(res.read())
    
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({
            "location": {"lat": lat, "lon": lon},
            "weather": data.get("current_weather", {})
        })
    }
EOF
```

### Step 3: SAMテンプレートを書き換え

```bash
cat > template.yaml << 'EOF'
AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2016-10-31
Description: Weather PoC - DVA-10 hands-on

Globals:
  Function:
    Timeout: 10
    MemorySize: 256
    Runtime: python3.13
    Tracing: Active

Resources:
  WeatherApi:
    Type: AWS::Serverless::Api
    Properties:
      StageName: prod
      CacheClusterEnabled: true
      CacheClusterSize: '0.5'
      MethodSettings:
        - ResourcePath: /*
          HttpMethod: '*'
          CachingEnabled: true
          CacheTtlInSeconds: 300

  WeatherFunction:
    Type: AWS::Serverless::Function
    Properties:
      CodeUri: hello_world/
      Handler: app.lambda_handler
      Events:
        WeatherGet:
          Type: Api
          Properties:
            RestApiId: !Ref WeatherApi
            Path: /weather
            Method: get

Outputs:
  WeatherApiUrl:
    Description: "API Gateway endpoint URL"
    Value: !Sub "https://${WeatherApi}.execute-api.${AWS::Region}.amazonaws.com/prod/weather"
EOF
```

### Step 4: ビルド・デプロイ

```bash
# ビルド
sam build

# デプロイ（初回）
sam deploy --guided
```

`sam deploy --guided` の質問への回答:

| 質問 | 入力値 |
|------|--------|
| Stack Name | `weather-poc` |
| AWS Region | `ap-northeast-1` |
| Confirm changes before deploy | `y` |
| Allow SAM CLI IAM role creation | `y` |
| Disable rollback | `n` |
| WeatherFunction may not have authorization defined, Is this okay? | `y` |
| Save arguments to configuration file | `y` |
| SAM configuration file | Enter |
| SAM configuration environment | Enter |

### Step 5: 動作テスト

```bash
# APIのURLを変数にセット（自動取得）
API_URL=$(aws cloudformation describe-stacks \
  --stack-name weather-poc \
  --query "Stacks[0].Outputs[0].OutputValue" \
  --output text)
echo $API_URL

# 1回目（キャッシュミス）
time curl -s "$API_URL?lat=35.68&lon=139.76" | python3 -m json.tool

# 2回目（キャッシュヒット → 速くなる）
time curl -s "$API_URL?lat=35.68&lon=139.76" | python3 -m json.tool

# 別の場所（キャッシュミスになる）
time curl -s "$API_URL?lat=35.90&lon=139.62" | python3 -m json.tool
```

### 後片付け

```bash
sam delete
# 2回 y を入力
```

### 学びポイント（DVA頻出）

- APIGWのキャッシュは `MethodSettings` で TTL を設定。クエリパラメータ単位でキャッシュキーが分かれる
- SAMの `AWS::Serverless::Function` はLambda + IAMロール + ロググループを一括生成
- `Tracing: Active` だけでX-Rayが有効化される
- バックエンドAPIの呼び出し回数削減 → コスト削減の典型パターン

### 完了チェックリスト

- [ ] sam init で weather-poc を作成した
- [ ] app.py を天気APIコードに書き換えた
- [ ] template.yaml にAPIGWキャッシュ設定を書いた
- [ ] sam build が成功した
- [ ] sam deploy でデプロイできた
- [ ] curl で天気データが返ってきた
- [ ] 1回目より2回目の方が速いことを確認した（キャッシュ効果）
- [ ] sam delete でリソースを削除した

---

## Day 2: バージョン・エイリアス・カナリアデプロイ

### ゴール

Lambdaのバージョン（$LATEST/数字）とエイリアスの関係を理解し、本番トラフィックを段階的に切り替える。

### 重要概念

```
$LATEST          ← 最新の編集中コード（本番では使わない）
Version 1, 2, 3  ← 不変のスナップショット
Alias prod       ← Version 2 を指す名前付きポインタ
                   weighted routing で Version 3 へ10%だけ流すことも可能
```

### Step 1: シンプルな関数を作成

```bash
mkdir -p version-demo && cd version-demo

cat > app.py << 'EOF'
import json

def lambda_handler(event, context):
    return {
        "statusCode": 200,
        "body": json.dumps({"version": "v1", "message": "Hello from Version 1"})
    }
EOF

zip function.zip app.py

# Lambda関数を作成
aws lambda create-function \
  --function-name version-demo \
  --runtime python3.13 \
  --handler app.lambda_handler \
  --zip-file fileb://function.zip \
  --role $(aws iam get-role --role-name lambda-basic-role --query 'Role.Arn' --output text 2>/dev/null || echo "ROLE_ARN_HERE")
```

> **注意**: `lambda-basic-role` が存在しない場合は、先にIAMロールを作成する必要がある。

```bash
# IAMロールが無い場合のみ実行
cat > trust-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {"Service": "lambda.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

aws iam create-role \
  --role-name lambda-basic-role \
  --assume-role-policy-document file://trust-policy.json

aws iam attach-role-policy \
  --role-name lambda-basic-role \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

# ロール作成後10秒ほど待ってからLambda作成を再実行
sleep 10

aws lambda create-function \
  --function-name version-demo \
  --runtime python3.13 \
  --handler app.lambda_handler \
  --zip-file fileb://function.zip \
  --role $(aws iam get-role --role-name lambda-basic-role --query 'Role.Arn' --output text)
```

### Step 2: バージョン1を発行

```bash
aws lambda publish-version --function-name version-demo
# → "Version": "1" が返る
```

### Step 3: エイリアス `prod` を作成して Version 1 を指す

```bash
aws lambda create-alias \
  --function-name version-demo \
  --name prod \
  --function-version 1
```

### Step 4: コードを更新して Version 2 を発行

```bash
cat > app.py << 'EOF'
import json

def lambda_handler(event, context):
    return {
        "statusCode": 200,
        "body": json.dumps({"version": "v2", "message": "Hello from Version 2 - improved!"})
    }
EOF

zip function.zip app.py

aws lambda update-function-code \
  --function-name version-demo \
  --zip-file fileb://function.zip

# 少し待ってからバージョン発行
sleep 3

aws lambda publish-version --function-name version-demo
# → "Version": "2" が返る
```

### Step 5: カナリアデプロイ（90% v1 / 10% v2）

```bash
aws lambda update-alias \
  --function-name version-demo \
  --name prod \
  --function-version 1 \
  --routing-config '{"AdditionalVersionWeights":{"2":0.1}}'
```

### Step 6: 動作確認（20回呼んでバージョン混在を確認）

```bash
for i in $(seq 1 20); do
  aws lambda invoke \
    --function-name version-demo:prod \
    --payload '{}' \
    /dev/stdout 2>/dev/null | head -1
done
```

大半が `"version": "v1"` で、数回だけ `"version": "v2"` が返る。

### Step 7: 全量切替（100% v2）

```bash
aws lambda update-alias \
  --function-name version-demo \
  --name prod \
  --function-version 2 \
  --routing-config '{}'
```

### SAMでの自動カナリアデプロイ（本番の本命）

`template.yaml` の Function に以下を追加するだけ:

```yaml
AutoPublishAlias: live
DeploymentPreference:
  Type: Canary10Percent10Minutes
  Alarms:
    - !Ref AliasErrorMetricGreaterThanZeroAlarm
```

DVA頻出パターン:

| 戦略 | 説明 |
|------|------|
| `Canary10Percent5Minutes` | 10%を5分間 → 全量切替 |
| `Canary10Percent10Minutes` | 10%を10分間 → 全量切替 |
| `Linear10PercentEvery1Minute` | 10%ずつ毎分増加 |
| `AllAtOnce` | 一気に切替（本番非推奨） |

### 後片付け

```bash
aws lambda delete-alias --function-name version-demo --name prod
aws lambda delete-function --function-name version-demo
aws iam detach-role-policy --role-name lambda-basic-role --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
aws iam delete-role --role-name lambda-basic-role
cd .. && rm -rf version-demo
```

### 完了チェックリスト

- [ ] Lambda関数を作成した
- [ ] Version 1 を発行した
- [ ] `prod` エイリアスを作成して Version 1 を指した
- [ ] コードを更新して Version 2 を発行した
- [ ] カナリア設定（90/10）を適用した
- [ ] 20回呼んで v1/v2 が混在することを確認した
- [ ] 全量 v2 に切り替えた
- [ ] リソースを削除した

---

## Day 3: Lambdaレイヤー + 設定管理

### ゴール

DBパスワードやAPIキーをコードに書かない設計を実装する。DVAの「ベストプラクティス」問題の正解パターン。

### Step 1: Lambdaレイヤーを作成

```bash
mkdir -p layer-demo/layer/python && cd layer-demo

# requests ライブラリをレイヤー用にインストール
pip install requests -t layer/python/ --quiet

# zipに固める
cd layer && zip -r ../requests-layer.zip python/ && cd ..

# レイヤーを発行
aws lambda publish-layer-version \
  --layer-name common-libs \
  --description "requests library" \
  --zip-file fileb://requests-layer.zip \
  --compatible-runtimes python3.13

# 返り値の LayerVersionArn をメモ
```

### Step 2: Parameter Store にパラメータを保存

```bash
aws ssm put-parameter \
  --name "/weather/api_timeout" \
  --value "5" \
  --type String

aws ssm put-parameter \
  --name "/weather/default_city" \
  --value "Tokyo" \
  --type String
```

### Step 3: Secrets Manager にAPIキーを保存

```bash
aws secretsmanager create-secret \
  --name weather-api-key \
  --secret-string '{"api_key":"demo-key-12345","api_secret":"demo-secret"}'
```

### Step 4: Lambda関数を作成

```bash
cat > app.py << 'EOF'
import json
import os
import boto3

ssm = boto3.client("ssm")
sm = boto3.client("secretsmanager")

# コールドスタート時のみ取得（ハンドラ外で初期化）
TIMEOUT = ssm.get_parameter(Name="/weather/api_timeout")["Parameter"]["Value"]
CITY = ssm.get_parameter(Name="/weather/default_city")["Parameter"]["Value"]
SECRET = json.loads(
    sm.get_secret_value(SecretId="weather-api-key")["SecretString"]
)

def lambda_handler(event, context):
    return {
        "statusCode": 200,
        "body": json.dumps({
            "timeout": TIMEOUT,
            "default_city": CITY,
            "api_key_last4": SECRET["api_key"][-4:],
            "env_log_level": os.environ.get("LOG_LEVEL", "not set"),
            "message": "Secrets and params loaded successfully"
        })
    }
EOF

zip function.zip app.py
```

IAMロールを作成（SSM + Secrets Manager の権限付き）:

```bash
cat > trust-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {"Service": "lambda.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

aws iam create-role \
  --role-name lambda-config-role \
  --assume-role-policy-document file://trust-policy.json

# 必要なポリシーをアタッチ
aws iam attach-role-policy --role-name lambda-config-role \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
aws iam attach-role-policy --role-name lambda-config-role \
  --policy-arn arn:aws:iam::aws:policy/AmazonSSMReadOnlyAccess
aws iam attach-role-policy --role-name lambda-config-role \
  --policy-arn arn:aws:iam::aws:policy/SecretsManagerReadWrite

sleep 10

LAYER_ARN=$(aws lambda list-layer-versions --layer-name common-libs \
  --query 'LayerVersions[0].LayerVersionArn' --output text)

aws lambda create-function \
  --function-name config-demo \
  --runtime python3.13 \
  --handler app.lambda_handler \
  --zip-file fileb://function.zip \
  --role $(aws iam get-role --role-name lambda-config-role --query 'Role.Arn' --output text) \
  --layers "$LAYER_ARN" \
  --environment 'Variables={LOG_LEVEL=INFO}' \
  --timeout 15
```

### Step 5: 動作確認

```bash
aws lambda invoke \
  --function-name config-demo \
  --payload '{}' \
  /dev/stdout 2>/dev/null | python3 -m json.tool
```

期待される出力:

```json
{
    "timeout": "5",
    "default_city": "Tokyo",
    "api_key_last4": "2345",
    "env_log_level": "INFO",
    "message": "Secrets and params loaded successfully"
}
```

### 試験頻出ポイント

| 観点 | Secrets Manager | SSM Parameter Store |
|------|-----------------|---------------------|
| 用途 | DB資格情報・APIキー | 一般的な設定値・フィーチャーフラグ |
| 自動ローテーション | あり | なし |
| コスト | 高い（$0.40/secret/月） | 安い（Standardは無料枠あり） |
| 暗号化 | デフォルト | SecureString指定時のみ |

- DB資格情報の自動ローテーション → Secrets Manager 一択
- レイヤーは1関数に最大5つまで、合計サイズ250MB制限
- 環境変数はKMSで暗号化可能

### 後片付け

```bash
aws lambda delete-function --function-name config-demo
aws lambda delete-layer-version --layer-name common-libs --version-number 1
aws ssm delete-parameter --name "/weather/api_timeout"
aws ssm delete-parameter --name "/weather/default_city"
aws secretsmanager delete-secret --secret-id weather-api-key --force-delete-without-recovery
aws iam detach-role-policy --role-name lambda-config-role --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
aws iam detach-role-policy --role-name lambda-config-role --policy-arn arn:aws:iam::aws:policy/AmazonSSMReadOnlyAccess
aws iam detach-role-policy --role-name lambda-config-role --policy-arn arn:aws:iam::aws:policy/SecretsManagerReadWrite
aws iam delete-role --role-name lambda-config-role
cd .. && rm -rf layer-demo
```

### 完了チェックリスト

- [ ] Lambdaレイヤーを作成してアタッチした
- [ ] Parameter Store にパラメータを保存し、Lambdaから取得した
- [ ] Secrets Manager にシークレットを保存し、Lambdaから取得した
- [ ] 環境変数 LOG_LEVEL が読めることを確認した
- [ ] リソースを全て削除した

---

## Day 4: 非同期呼び出し + DLQ + イベントソースマッピング

### ゴール

SQS/SNSとLambdaの統合パターンを実装し、失敗時の挙動を体感する。

### 構成図

```
SNS Topic ──┬──> SQS Queue ──> Lambda(Consumer) ──> 失敗時 ──> DLQ
            └──> Email（確認用）
```

### Step 1: SQSキューとDLQを作成

```bash
mkdir -p async-demo && cd async-demo

# DLQ（デッドレターキュー）を先に作成
aws sqs create-queue --queue-name order-dlq
DLQ_ARN=$(aws sqs get-queue-attributes \
  --queue-url $(aws sqs get-queue-url --queue-name order-dlq --query 'QueueUrl' --output text) \
  --attribute-names QueueArn --query 'Attributes.QueueArn' --output text)

# メインキュー（3回失敗したらDLQに送る）
aws sqs create-queue --queue-name order-queue \
  --attributes "{\"RedrivePolicy\":\"{\\\"deadLetterTargetArn\\\":\\\"$DLQ_ARN\\\",\\\"maxReceiveCount\\\":\\\"3\\\"}\"}"

QUEUE_URL=$(aws sqs get-queue-url --queue-name order-queue --query 'QueueUrl' --output text)
QUEUE_ARN=$(aws sqs get-queue-attributes --queue-url $QUEUE_URL \
  --attribute-names QueueArn --query 'Attributes.QueueArn' --output text)
```

### Step 2: Lambda関数を作成（わざと失敗する機能付き）

```bash
cat > app.py << 'EOF'
import json

def lambda_handler(event, context):
    for record in event["Records"]:
        body = json.loads(record["body"])
        print(f"Processing: {body}")
        
        if body.get("force_fail"):
            print(f"INTENTIONAL FAILURE for: {body['id']}")
            raise Exception("Intentional failure for DLQ demo")
        
        print(f"SUCCESS: Processed order {body.get('id', 'unknown')}")
    
    return {"statusCode": 200}
EOF

zip function.zip app.py

# IAMロール作成
cat > trust-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {"Service": "lambda.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

aws iam create-role --role-name lambda-sqs-role \
  --assume-role-policy-document file://trust-policy.json

aws iam attach-role-policy --role-name lambda-sqs-role \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
aws iam attach-role-policy --role-name lambda-sqs-role \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaSQSQueueExecutionRole

sleep 10

aws lambda create-function \
  --function-name order-processor \
  --runtime python3.13 \
  --handler app.lambda_handler \
  --zip-file fileb://function.zip \
  --role $(aws iam get-role --role-name lambda-sqs-role --query 'Role.Arn' --output text) \
  --timeout 10
```

### Step 3: SQS → Lambda のイベントソースマッピングを作成

```bash
aws lambda create-event-source-mapping \
  --function-name order-processor \
  --event-source-arn $QUEUE_ARN \
  --batch-size 5
```

### Step 4: 正常メッセージを送信して処理されることを確認

```bash
aws sqs send-message --queue-url $QUEUE_URL \
  --message-body '{"id": "order-001", "item": "laptop", "force_fail": false}'

# 数秒待ってからCloudWatch Logsで確認
sleep 5
aws logs tail /aws/lambda/order-processor --since 2m
```

### Step 5: 失敗メッセージを送信してDLQ行きを確認

```bash
aws sqs send-message --queue-url $QUEUE_URL \
  --message-body '{"id": "order-002", "item": "phone", "force_fail": true}'

# 3回リトライされるので約1〜2分待つ
echo "Waiting for 3 retries..."
sleep 90

# DLQにメッセージが入っているか確認
DLQ_URL=$(aws sqs get-queue-url --queue-name order-dlq --query 'QueueUrl' --output text)
aws sqs receive-message --queue-url $DLQ_URL
```

DLQからメッセージが返ってくれば成功。3回失敗した後にDLQに移動したことが確認できる。

### 試験頻出ポイント

| 概念 | キーワード |
|------|-----------|
| Visibility Timeout | Lambda タイムアウト × 6倍が推奨 |
| 同時実行数の制御 | `ReservedConcurrency` で予約 |
| 部分バッチ失敗 | `ReportBatchItemFailures` で成功分は削除 |
| 順序保証 | SQS FIFO + MessageGroupId |
| 非同期呼び出し最大リトライ | デフォルト2回（計3回実行） |

### 後片付け

```bash
# イベントソースマッピングを削除
EVENT_UUID=$(aws lambda list-event-source-mappings \
  --function-name order-processor \
  --query 'EventSourceMappings[0].UUID' --output text)
aws lambda delete-event-source-mapping --uuid $EVENT_UUID

aws lambda delete-function --function-name order-processor
aws sqs delete-queue --queue-url $QUEUE_URL
aws sqs delete-queue --queue-url $DLQ_URL
aws iam detach-role-policy --role-name lambda-sqs-role --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
aws iam detach-role-policy --role-name lambda-sqs-role --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaSQSQueueExecutionRole
aws iam delete-role --role-name lambda-sqs-role
cd .. && rm -rf async-demo
```

### 完了チェックリスト

- [ ] SQSメインキューとDLQを作成した
- [ ] Lambda関数を作成してSQSトリガーを設定した
- [ ] 正常メッセージが処理されることを確認した
- [ ] 失敗メッセージが3回リトライ後にDLQに移動することを確認した
- [ ] リソースを全て削除した

---

## Day 5: プロビジョンド同時実行 + X-Ray + CloudWatch

### ゴール

コールドスタートの計測と対策、可観測性の確立。

### Step 1: Day 1の天気APIを再デプロイ

```bash
cd weather-poc
sam build
sam deploy
```

### Step 2: コールドスタートを計測

```bash
API_URL=$(aws cloudformation describe-stacks \
  --stack-name weather-poc \
  --query "Stacks[0].Outputs[0].OutputValue" \
  --output text)

# 10回連続で呼んでレスポンス時間を計測
for i in $(seq 1 10); do
  echo -n "Request $i: "
  curl -s -w "%{time_total}s\n" -o /dev/null "$API_URL?lat=35.68&lon=139.76"
done
```

1回目が遅い（コールドスタート）。

### Step 3: CloudWatch Logs Insights でコールドスタートを可視化

AWSコンソール → CloudWatch → Logs Insights で以下のクエリを実行:

```sql
fields @timestamp, @initDuration, @duration, @memorySize, @maxMemoryUsed
| filter @type = "REPORT"
| sort @timestamp desc
| limit 20
```

`@initDuration` がある行がコールドスタート。

### Step 4: Provisioned Concurrency を設定

```bash
FUNCTION_NAME=$(aws cloudformation describe-stack-resources \
  --stack-name weather-poc \
  --query "StackResources[?ResourceType=='AWS::Lambda::Function'].PhysicalResourceId" \
  --output text)

# まずバージョンを発行
VERSION=$(aws lambda publish-version \
  --function-name $FUNCTION_NAME \
  --query 'Version' --output text)

# エイリアス作成
aws lambda create-alias \
  --function-name $FUNCTION_NAME \
  --name warm \
  --function-version $VERSION

# Provisioned Concurrency を設定（5インスタンス常時起動）
aws lambda put-provisioned-concurrency-config \
  --function-name $FUNCTION_NAME \
  --qualifier warm \
  --provisioned-concurrent-executions 5

# 準備完了まで待つ（1〜2分）
aws lambda get-provisioned-concurrency-config \
  --function-name $FUNCTION_NAME \
  --qualifier warm
# Status: READY になるまで待つ
```

### Step 5: コールドスタートが消えたことを確認

```bash
# エイリアス経由で呼ぶ
for i in $(seq 1 10); do
  echo -n "Request $i: "
  aws lambda invoke \
    --function-name "$FUNCTION_NAME:warm" \
    --payload '{"queryStringParameters":{"lat":"35.68","lon":"139.76"}}' \
    /dev/stdout 2>/dev/null | head -c 0
  echo ""
done
```

### Step 6: X-Ray サービスマップを確認

AWSコンソール → CloudWatch → X-Ray traces → サービスマップ

API Gateway → Lambda → 外部APIの依存関係とレイテンシが可視化される。

### 試験頻出表（必ず暗記）

| 設定 | 用途 | 課金 |
|------|------|------|
| Reserved Concurrency | 同時実行数の上限（他関数からの圧迫を防ぐ） | 無料 |
| Provisioned Concurrency | コールドスタートゼロ化 | 有料 |
| Unreserved Concurrency | アカウントの残り枠（デフォルト1000） | - |

### 後片付け

```bash
# Provisioned Concurrency を削除
aws lambda delete-provisioned-concurrency-config \
  --function-name $FUNCTION_NAME \
  --qualifier warm

# エイリアス削除
aws lambda delete-alias --function-name $FUNCTION_NAME --name warm

# スタック全体削除
sam delete
```

### 完了チェックリスト

- [ ] コールドスタートの時間を計測した
- [ ] CloudWatch Logs Insights で @initDuration を確認した
- [ ] Provisioned Concurrency を設定した
- [ ] コールドスタートが消えたことを確認した
- [ ] X-Ray サービスマップを確認した
- [ ] リソースを全て削除した

---

# Week 3 — DynamoDB + Step Functions + CI/CD

---

## Day 1: DynamoDB基礎 + キー設計

### ゴール

パーティションキー/ソートキーの設計と、GSI/LSIの使い分けを体得する。

### Step 1: テーブル作成

```bash
aws dynamodb create-table \
  --table-name UserOrders \
  --attribute-definitions \
      AttributeName=UserId,AttributeType=S \
      AttributeName=OrderDate,AttributeType=S \
      AttributeName=Status,AttributeType=S \
  --key-schema \
      AttributeName=UserId,KeyType=HASH \
      AttributeName=OrderDate,KeyType=RANGE \
  --global-secondary-indexes \
      '[{
          "IndexName": "StatusDateIndex",
          "KeySchema": [
              {"AttributeName": "Status", "KeyType": "HASH"},
              {"AttributeName": "OrderDate", "KeyType": "RANGE"}
          ],
          "Projection": {"ProjectionType": "ALL"}
      }]' \
  --billing-mode PAY_PER_REQUEST

aws dynamodb wait table-exists --table-name UserOrders
echo "Table created!"
```

### Step 2: データを投入

```bash
aws dynamodb batch-write-item --request-items '{
  "UserOrders": [
    {"PutRequest": {"Item": {"UserId": {"S": "user-001"}, "OrderDate": {"S": "2026-05-01"}, "Status": {"S": "shipped"}, "Item": {"S": "Laptop"}, "Amount": {"N": "1200"}}}},
    {"PutRequest": {"Item": {"UserId": {"S": "user-001"}, "OrderDate": {"S": "2026-05-05"}, "Status": {"S": "pending"}, "Item": {"S": "Mouse"}, "Amount": {"N": "50"}}}},
    {"PutRequest": {"Item": {"UserId": {"S": "user-001"}, "OrderDate": {"S": "2026-05-10"}, "Status": {"S": "delivered"}, "Item": {"S": "Keyboard"}, "Amount": {"N": "150"}}}},
    {"PutRequest": {"Item": {"UserId": {"S": "user-002"}, "OrderDate": {"S": "2026-05-03"}, "Status": {"S": "shipped"}, "Item": {"S": "Monitor"}, "Amount": {"N": "800"}}}},
    {"PutRequest": {"Item": {"UserId": {"S": "user-002"}, "OrderDate": {"S": "2026-05-08"}, "Status": {"S": "pending"}, "Item": {"S": "Webcam"}, "Amount": {"N": "120"}}}},
    {"PutRequest": {"Item": {"UserId": {"S": "user-003"}, "OrderDate": {"S": "2026-05-02"}, "Status": {"S": "delivered"}, "Item": {"S": "Headphones"}, "Amount": {"N": "300"}}}}
  ]
}'
```

### Step 3: クエリパターンを試す

**パターン1: ユーザーの全注文を取得（PK指定）**

```bash
aws dynamodb query \
  --table-name UserOrders \
  --key-condition-expression "UserId = :uid" \
  --expression-attribute-values '{":uid": {"S": "user-001"}}' \
  --output table
```

**パターン2: ユーザーの特定日以降の注文（PK + SK範囲）**

```bash
aws dynamodb query \
  --table-name UserOrders \
  --key-condition-expression "UserId = :uid AND OrderDate >= :d" \
  --expression-attribute-values '{":uid": {"S": "user-001"}, ":d": {"S": "2026-05-05"}}' \
  --output table
```

**パターン3: ステータス別の注文一覧（GSI使用）**

```bash
aws dynamodb query \
  --table-name UserOrders \
  --index-name StatusDateIndex \
  --key-condition-expression "#s = :status" \
  --expression-attribute-names '{"#s": "Status"}' \
  --expression-attribute-values '{":status": {"S": "shipped"}}' \
  --output table
```

### 試験頻出

| 概念 | 説明 |
|------|------|
| PK（パーティションキー） | データの振り分け先。高カーディナリティが必須 |
| SK（ソートキー） | PK内の並び順。範囲検索が可能 |
| GSI | PK/SKを別キーで再定義。テーブル作成後も追加可 |
| LSI | SKだけ変更。テーブル作成時のみ追加可 |
| RCU | 1RCU = 4KB の強整合読み取り1回 / 結果整合なら2回 |
| WCU | 1WCU = 1KB の書き込み1回 |
| ホットパーティション対策 | PKを高カーディナリティにする（ユーザーID○、日付×） |

### 後片付け

```bash
aws dynamodb delete-table --table-name UserOrders
```

### 完了チェックリスト

- [ ] PK + SK のテーブルを作成した
- [ ] GSIを作成して別のアクセスパターンでクエリした
- [ ] PK指定、PK+SK範囲指定、GSI指定の3パターンを試した
- [ ] テーブルを削除した

---

## Day 2: Streams + TTL + トランザクション

### ゴール

DynamoDB Streamsによる変更データキャプチャ、TTLの自動削除、トランザクションの原子操作を体験する。

### Step 1: Streams付きテーブル作成

```bash
aws dynamodb create-table \
  --table-name SessionStore \
  --attribute-definitions AttributeName=SessionId,AttributeType=S \
  --key-schema AttributeName=SessionId,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --stream-specification StreamEnabled=true,StreamViewType=NEW_AND_OLD_IMAGES

aws dynamodb wait table-exists --table-name SessionStore
```

### Step 2: TTLを有効化

```bash
aws dynamodb update-time-to-live \
  --table-name SessionStore \
  --time-to-live-specification "Enabled=true, AttributeName=ExpiresAt"
```

### Step 3: TTL付きデータを投入

```bash
# 現在時刻 + 60秒後にTTLが切れるデータ
EXPIRE=$(date -d "+60 seconds" +%s 2>/dev/null || date -v+60S +%s)

aws dynamodb put-item --table-name SessionStore \
  --item "{
    \"SessionId\": {\"S\": \"sess-001\"},
    \"User\": {\"S\": \"alice\"},
    \"ExpiresAt\": {\"N\": \"$EXPIRE\"}
  }"

echo "Item will expire at: $(date -d @$EXPIRE 2>/dev/null || date -r $EXPIRE)"
```

> **注意**: TTLの実際の削除はAWSが非同期で行うため、数分〜48時間のラグがある。

### Step 4: トランザクションを試す

```bash
# 在庫テーブル作成
aws dynamodb create-table \
  --table-name Inventory \
  --attribute-definitions AttributeName=ProductId,AttributeType=S \
  --key-schema AttributeName=ProductId,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST
aws dynamodb wait table-exists --table-name Inventory

# 在庫データ投入
aws dynamodb put-item --table-name Inventory \
  --item '{"ProductId":{"S":"prod-001"},"Stock":{"N":"10"},"Name":{"S":"Laptop"}}'

# トランザクション: 在庫-1 と セッション更新 を原子的に実行
aws dynamodb transact-write-items --transact-items '[
  {
    "Update": {
      "TableName": "Inventory",
      "Key": {"ProductId": {"S": "prod-001"}},
      "UpdateExpression": "SET Stock = Stock - :dec",
      "ConditionExpression": "Stock > :zero",
      "ExpressionAttributeValues": {":dec": {"N": "1"}, ":zero": {"N": "0"}}
    }
  },
  {
    "Put": {
      "TableName": "SessionStore",
      "Item": {
        "SessionId": {"S": "order-tx-001"},
        "User": {"S": "bob"},
        "Action": {"S": "purchased prod-001"}
      }
    }
  }
]'

# 在庫が9になっていることを確認
aws dynamodb get-item --table-name Inventory \
  --key '{"ProductId":{"S":"prod-001"}}' \
  --query 'Item.Stock.N' --output text
# → 9
```

### 後片付け

```bash
aws dynamodb delete-table --table-name SessionStore
aws dynamodb delete-table --table-name Inventory
```

### 完了チェックリスト

- [ ] Streams付きテーブルを作成した
- [ ] TTLを有効化してデータを投入した
- [ ] トランザクションで在庫減算+注文作成を原子的に実行した
- [ ] テーブルを削除した

---

## Day 3: Step Functions

### ゴール

複数Lambdaの逐次/並列実行、条件分岐をStep Functionsで実装する。

### Standard vs Express（超頻出）

| | Standard | Express |
|-|----------|---------|
| 実行時間上限 | 1年 | 5分 |
| 課金 | 状態遷移ごと | 実行時間+回数 |
| 実行履歴 | 完全保持 | CloudWatch Logsのみ |
| ユースケース | 長時間ETL・人手承認 | 高頻度API・IoT |

### Step 1: 2つのLambda関数を作成

```bash
mkdir -p sfn-demo && cd sfn-demo

# 関数1: 注文バリデーション
cat > validate.py << 'EOF'
import json
def lambda_handler(event, context):
    order = event
    if order.get("amount", 0) <= 0:
        return {"status": "INVALID", "reason": "Amount must be positive"}
    if not order.get("item"):
        return {"status": "INVALID", "reason": "Item is required"}
    return {"status": "VALID", "order": order}
EOF
zip validate.zip validate.py

# 関数2: 注文処理
cat > process.py << 'EOF'
import json
import random
import string
def lambda_handler(event, context):
    order = event.get("order", event)
    order_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    return {
        "status": "COMPLETED",
        "order_id": order_id,
        "item": order.get("item"),
        "amount": order.get("amount")
    }
EOF
zip process.zip process.py

# IAMロール
cat > trust-policy.json << 'EOF'
{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"lambda.amazonaws.com"},"Action":"sts:AssumeRole"}]}
EOF

aws iam create-role --role-name lambda-sfn-role --assume-role-policy-document file://trust-policy.json
aws iam attach-role-policy --role-name lambda-sfn-role --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
sleep 10

ROLE_ARN=$(aws iam get-role --role-name lambda-sfn-role --query 'Role.Arn' --output text)

aws lambda create-function --function-name validate-order --runtime python3.13 \
  --handler validate.lambda_handler --zip-file fileb://validate.zip --role $ROLE_ARN
aws lambda create-function --function-name process-order --runtime python3.13 \
  --handler process.lambda_handler --zip-file fileb://process.zip --role $ROLE_ARN

VALIDATE_ARN=$(aws lambda get-function --function-name validate-order --query 'Configuration.FunctionArn' --output text)
PROCESS_ARN=$(aws lambda get-function --function-name process-order --query 'Configuration.FunctionArn' --output text)
```

### Step 2: Step Functions ステートマシン定義

```bash
cat > state-machine.json << EOF
{
  "Comment": "Order Processing Workflow",
  "StartAt": "ValidateOrder",
  "States": {
    "ValidateOrder": {
      "Type": "Task",
      "Resource": "$VALIDATE_ARN",
      "Next": "CheckValidation"
    },
    "CheckValidation": {
      "Type": "Choice",
      "Choices": [
        {
          "Variable": "$.status",
          "StringEquals": "VALID",
          "Next": "ProcessOrder"
        }
      ],
      "Default": "OrderRejected"
    },
    "ProcessOrder": {
      "Type": "Task",
      "Resource": "$PROCESS_ARN",
      "Next": "OrderCompleted"
    },
    "OrderCompleted": {
      "Type": "Succeed"
    },
    "OrderRejected": {
      "Type": "Fail",
      "Error": "ValidationError",
      "Cause": "Order validation failed"
    }
  }
}
EOF
```

### Step 3: ステートマシン作成

```bash
# Step Functions 用 IAMロール
cat > sfn-trust.json << 'EOF'
{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"states.amazonaws.com"},"Action":"sts:AssumeRole"}]}
EOF

aws iam create-role --role-name sfn-execution-role --assume-role-policy-document file://sfn-trust.json
aws iam attach-role-policy --role-name sfn-execution-role --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaRole

sleep 10

SFN_ROLE_ARN=$(aws iam get-role --role-name sfn-execution-role --query 'Role.Arn' --output text)

aws stepfunctions create-state-machine \
  --name order-workflow \
  --definition file://state-machine.json \
  --role-arn $SFN_ROLE_ARN

SFN_ARN=$(aws stepfunctions list-state-machines \
  --query "stateMachines[?name=='order-workflow'].stateMachineArn" --output text)
```

### Step 4: 正常パターンで実行

```bash
aws stepfunctions start-execution \
  --state-machine-arn $SFN_ARN \
  --input '{"item": "Laptop", "amount": 1200}'

# 数秒待ってから結果確認
sleep 5
EXEC_ARN=$(aws stepfunctions list-executions \
  --state-machine-arn $SFN_ARN \
  --query 'executions[0].executionArn' --output text)

aws stepfunctions describe-execution \
  --execution-arn $EXEC_ARN \
  --query '{status: status, output: output}'
```

### Step 5: 異常パターン（バリデーション失敗）

```bash
aws stepfunctions start-execution \
  --state-machine-arn $SFN_ARN \
  --input '{"item": "", "amount": 0}'

sleep 5
EXEC_ARN=$(aws stepfunctions list-executions \
  --state-machine-arn $SFN_ARN \
  --query 'executions[0].executionArn' --output text)

aws stepfunctions describe-execution \
  --execution-arn $EXEC_ARN \
  --query '{status: status, error: error, cause: cause}'
# → status: FAILED
```

### Step 6: AWSコンソールで実行フローを確認

Step Functions コンソール → order-workflow → 実行をクリック → グラフビューで各ステートの遷移を視覚的に確認。

### 後片付け

```bash
aws stepfunctions delete-state-machine --state-machine-arn $SFN_ARN
aws lambda delete-function --function-name validate-order
aws lambda delete-function --function-name process-order
aws iam detach-role-policy --role-name lambda-sfn-role --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
aws iam delete-role --role-name lambda-sfn-role
aws iam detach-role-policy --role-name sfn-execution-role --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaRole
aws iam delete-role --role-name sfn-execution-role
cd .. && rm -rf sfn-demo
```

### 完了チェックリスト

- [ ] 2つのLambda関数を作成した
- [ ] Choice ステートで条件分岐するステートマシンを作成した
- [ ] 正常パターンで SUCCEEDED を確認した
- [ ] 異常パターンで FAILED を確認した
- [ ] コンソールでグラフビューを確認した
- [ ] リソースを全て削除した

---

## Day 4: CodeBuild

### ゴール

`buildspec.yml` の構造を理解し、SAMアプリのビルドを自動化する。

### buildspec.yml の5フェーズ（試験頻出）

```
install     → ランタイム・ツールのインストール
pre_build   → 依存関係のインストール・テスト
build       → コンパイル・パッケージング
post_build  → 成果物のアップロード・通知
reports     → テストレポート（オプション）
```

### Step 1: S3バケットを作成（ビルド成果物用）

```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ARTIFACT_BUCKET="codebuild-artifacts-${ACCOUNT_ID}"

aws s3 mb s3://$ARTIFACT_BUCKET
```

### Step 2: buildspec.yml を作成

```bash
mkdir -p codebuild-demo && cd codebuild-demo

cat > buildspec.yml << 'EOF'
version: 0.2

phases:
  install:
    runtime-versions:
      python: 3.12
    commands:
      - echo "=== Install Phase ==="
      - pip install --upgrade pip

  pre_build:
    commands:
      - echo "=== Pre-Build Phase ==="
      - echo "Running tests..."
      - python -m pytest tests/ -v 2>/dev/null || echo "No tests found, skipping"

  build:
    commands:
      - echo "=== Build Phase ==="
      - echo "Building application..."
      - zip -r app.zip app.py

  post_build:
    commands:
      - echo "=== Post-Build Phase ==="
      - echo "Build completed on $(date)"

artifacts:
  files:
    - app.zip
    - buildspec.yml
EOF
```

### Step 3: ソースコードを用意してS3にアップロード

```bash
cat > app.py << 'EOF'
def handler(event, context):
    return {"statusCode": 200, "body": "Built by CodeBuild"}
EOF

zip source.zip app.py buildspec.yml
aws s3 cp source.zip s3://$ARTIFACT_BUCKET/source.zip
```

### Step 4: CodeBuild プロジェクトを作成

```bash
cat > codebuild-project.json << EOF
{
  "name": "weather-build",
  "source": {
    "type": "S3",
    "location": "${ARTIFACT_BUCKET}/source.zip"
  },
  "artifacts": {
    "type": "S3",
    "location": "${ARTIFACT_BUCKET}",
    "name": "build-output"
  },
  "environment": {
    "type": "LINUX_CONTAINER",
    "computeType": "BUILD_GENERAL1_SMALL",
    "image": "aws/codebuild/amazonlinux2-x86_64-standard:5.0"
  },
  "serviceRole": "arn:aws:iam::${ACCOUNT_ID}:role/codebuild-service-role"
}
EOF
```

> **注意**: CodeBuild用のサービスロールが必要。以下で作成する。

```bash
cat > codebuild-trust.json << 'EOF'
{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"codebuild.amazonaws.com"},"Action":"sts:AssumeRole"}]}
EOF

aws iam create-role --role-name codebuild-service-role --assume-role-policy-document file://codebuild-trust.json
aws iam attach-role-policy --role-name codebuild-service-role --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess
aws iam attach-role-policy --role-name codebuild-service-role --policy-arn arn:aws:iam::aws:policy/CloudWatchLogsFullAccess

sleep 10

# プロジェクト作成（JSONのACCOUNT_IDを置換）
sed -i "s/\${ACCOUNT_ID}/$ACCOUNT_ID/g" codebuild-project.json
aws codebuild create-project --cli-input-json file://codebuild-project.json
```

### Step 5: ビルドを実行

```bash
BUILD_ID=$(aws codebuild start-build --project-name weather-build \
  --query 'build.id' --output text)

echo "Build started: $BUILD_ID"

# ビルド完了を待つ
aws codebuild batch-get-builds --ids $BUILD_ID \
  --query 'builds[0].buildStatus'
# IN_PROGRESS → SUCCEEDED になるまで数分待つ
```

### 後片付け

```bash
aws codebuild delete-project --name weather-build
aws s3 rb s3://$ARTIFACT_BUCKET --force
aws iam detach-role-policy --role-name codebuild-service-role --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess
aws iam detach-role-policy --role-name codebuild-service-role --policy-arn arn:aws:iam::aws:policy/CloudWatchLogsFullAccess
aws iam delete-role --role-name codebuild-service-role
cd .. && rm -rf codebuild-demo
```

### 完了チェックリスト

- [ ] buildspec.yml の5フェーズを書いた
- [ ] CodeBuild プロジェクトを作成した
- [ ] ビルドを実行して SUCCEEDED を確認した
- [ ] リソースを全て削除した

---

## Day 5: CodeDeploy + CodePipeline（Lambda CI/CD）

### ゴール

SAMの `DeploymentPreference` を使ったLambda CI/CDパイプラインを構築する。

### Lambda向けデプロイ戦略（試験頻出）

| 戦略 | 説明 |
|------|------|
| `Canary10Percent5Minutes` | 10%を5分間 → 残り全部 |
| `Linear10PercentEvery1Minute` | 10%ずつ毎分増加 |
| `AllAtOnce` | 一気に切替（本番非推奨） |

### ハンズオン

Day 2 で体験したカナリアデプロイを、SAMテンプレートに組み込むだけ:

```yaml
# template.yaml の WeatherFunction に追加
AutoPublishAlias: live
DeploymentPreference:
  Type: Canary10Percent5Minutes
```

`sam deploy` するたびにCodeDeployが自動で段階的デプロイを実行する。

### CodePipeline の基本構成（概念理解）

```
Source（GitHub/CodeCommit）
    ↓
Build（CodeBuild → sam build → sam package）
    ↓
Deploy（CloudFormation → CodeDeploy でカナリア/リニア）
```

EC2/ECS向けの Blue/Green や In-Place とは別物。DVAではLambda向けを最優先で覚える。

### 完了チェックリスト

- [ ] SAMテンプレートに DeploymentPreference を追加した
- [ ] デプロイ時にCodeDeployが段階的に切り替えることを確認した
- [ ] CodePipelineの3ステージ構成を理解した

---

## Day 6: Cognito + API Gateway認証

### ゴール

API Gatewayの認証パターンを理解し、Cognito User Poolでの認証を実装する。

### 3種類のオーソライザー（超頻出）

| タイプ | 用途 |
|--------|------|
| Cognito User Pools Authorizer | JWT検証のみ（シンプル） |
| Lambda Authorizer (TOKEN) | カスタムロジック（IPチェック等） |
| Lambda Authorizer (REQUEST) | ヘッダー/パス/クエリで判定 |
| IAM Authorization | SigV4署名（M2M認証） |

### User Pool vs Identity Pool

| | User Pool | Identity Pool |
|-|-----------|---------------|
| 目的 | 認証（ログイン・サインアップ） | 認可（AWSリソースへの一時クレデンシャル発行） |
| 返すもの | JWT トークン | IAM 一時認証情報 |
| 用途 | API Gatewayの認証 | S3やDynamoDBへの直接アクセス |

### Step 1: Cognito User Pool を作成

```bash
POOL_ID=$(aws cognito-idp create-user-pool \
  --pool-name weather-users \
  --auto-verified-attributes email \
  --query 'UserPool.Id' --output text)

echo "User Pool ID: $POOL_ID"

# アプリクライアント作成
CLIENT_ID=$(aws cognito-idp create-user-pool-client \
  --user-pool-id $POOL_ID \
  --client-name weather-app \
  --explicit-auth-flows ALLOW_USER_PASSWORD_AUTH ALLOW_REFRESH_TOKEN_AUTH \
  --query 'UserPoolClient.ClientId' --output text)

echo "Client ID: $CLIENT_ID"
```

### Step 2: テストユーザーを作成

```bash
aws cognito-idp admin-create-user \
  --user-pool-id $POOL_ID \
  --username testuser \
  --temporary-password 'TempPass123!' \
  --message-action SUPPRESS

aws cognito-idp admin-set-user-password \
  --user-pool-id $POOL_ID \
  --username testuser \
  --password 'TestPass123!' \
  --permanent
```

### Step 3: トークンを取得

```bash
TOKEN=$(aws cognito-idp initiate-auth \
  --client-id $CLIENT_ID \
  --auth-flow USER_PASSWORD_AUTH \
  --auth-parameters USERNAME=testuser,PASSWORD='TestPass123!' \
  --query 'AuthenticationResult.IdToken' --output text)

echo "Token (first 50 chars): ${TOKEN:0:50}..."
```

### Step 4: SAMテンプレートにCognito認証を追加

Day 1 の weather-poc を拡張する場合:

```yaml
Resources:
  WeatherApi:
    Type: AWS::Serverless::Api
    Properties:
      StageName: prod
      Auth:
        DefaultAuthorizer: CognitoAuthorizer
        Authorizers:
          CognitoAuthorizer:
            UserPoolArn: !GetAtt CognitoUserPool.Arn

  CognitoUserPool:
    Type: AWS::Cognito::UserPool
    Properties:
      UserPoolName: weather-users
```

### Step 5: 認証あり/なしでリクエスト

```bash
# 認証なし → 401 Unauthorized
curl -s "https://xxx.execute-api.../prod/weather"

# 認証あり → 200 OK
curl -s -H "Authorization: $TOKEN" "https://xxx.execute-api.../prod/weather"
```

### 後片付け

```bash
aws cognito-idp delete-user-pool --user-pool-id $POOL_ID
```

### 完了チェックリスト

- [ ] Cognito User Pool を作成した
- [ ] テストユーザーを作成してトークンを取得した
- [ ] 認証なしで 401、認証ありで 200 を確認した
- [ ] リソースを削除した

---

## Day 7: 模擬試験 + 誤答ノート整備

### やること

1. TutorialsDojo Practice Exam Set 1 を実施
2. 正答率70%未満の分野を特定
3. 弱点ノートを作成

### 誤答ノートのフォーマット

```markdown
## 問題番号: XX
- 自分の回答: B
- 正解: D
- なぜ正解が D か: [根拠]
- なぜ B がダメか: [理由]
- 関連するハンズオン: Day X
- 覚えるキーワード: [暗記事項]
```

---

# 進捗チェックリスト（全体）

Week 2.5 と Week 3 を全て終えたら、以下が説明できる/作れる状態になる。

```
□ SAMで Lambda + APIGW（Cache有効）を1コマンドでデプロイできる
□ Canary10Percent5Minutes の意味と設定箇所を即答できる
□ Reserved vs Provisioned Concurrency を使い分けられる
□ SQS Visibility Timeout と Lambda Timeout の関係を説明できる
□ DynamoDB の GSI/LSI の違いを実機で示せる
□ Step Functions Standard vs Express の選び方を即答できる
□ buildspec.yml の5フェーズを書ける
□ Cognito User Pool と Identity Pool の役割の違いを説明できる
```

このチェックリストが全部チェック済みになれば、DVA合格ラインの70%以上は確実。