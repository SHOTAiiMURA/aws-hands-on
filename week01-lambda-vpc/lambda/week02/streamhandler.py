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