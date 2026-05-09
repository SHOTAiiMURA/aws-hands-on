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