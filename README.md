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