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
        else:
            logger.info(f"画像以外のファイル: {object_key}")

    return {
        'statusCode': 200,
        'body': json.dumps({
            'message': 'S3 イベントを正常に処理しました',
            'processed_records': len(event['Records'])
        }, ensure_ascii=False)
    }