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

            existing = table.get_item(Key={'id': item_id})
            if 'Item' not in existing:
                return response(404, {'error': f'Item {item_id} が見つかりません'})

            update_parts = []
            expression_values = {}
            expression_names = {}

            for key, value in item_data.items():
                if key == 'id':
                    continue
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