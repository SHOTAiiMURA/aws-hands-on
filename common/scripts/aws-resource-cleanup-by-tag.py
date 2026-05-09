"""
AWS リソース一括削除スクリプト
指定したタグが付与されたリソースを検索し、確認後に削除します。

使い方:
  python cleanup_by_tag.py                    # デフォルト: Key=aws-hands-on, Value=01
  python cleanup_by_tag.py --value 02         # Value を変更して Week 02 のリソースを削除
  python cleanup_by_tag.py --dry-run           # 削除対象の確認のみ（実際には削除しない）
"""

import boto3
import argparse
import json


# ========== 設定 ==========

TAG_KEY = "aws-hands-on"
DEFAULT_TAG_VALUE = "01"
REGION = "ap-northeast-1"

# ========== 色付きターミナル出力 ==========

class Color:
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    END = "\033[0m"


def print_header(text):
    print(f"\n{Color.BOLD}{Color.CYAN}{'=' * 60}")
    print(f"  {text}")
    print(f"{'=' * 60}{Color.END}")


def print_found(resource_type, name):
    print(f"  {Color.YELLOW}[検出]{Color.END} {resource_type}: {Color.BOLD}{name}{Color.END}")


def print_deleted(resource_type, name):
    print(f"  {Color.GREEN}[削除完了]{Color.END} {resource_type}: {name}")


def print_error(resource_type, name, error):
    print(f"  {Color.RED}[エラー]{Color.END} {resource_type}: {name} - {error}")


def print_skip(reason):
    print(f"  {Color.YELLOW}[スキップ]{Color.END} {reason}")


# ========== タグ付きリソースの検索 ==========

def find_tagged_resources(tag_key, tag_value):
    """Resource Groups Tagging API でタグ付きリソースを一括検索"""
    client = boto3.client("resourcegroupstaggingapi", region_name=REGION)
    resources = []
    paginator = client.get_paginator("get_resources")

    for page in paginator.paginate(
        TagFilters=[{"Key": tag_key, "Values": [tag_value]}]
    ):
        resources.extend(page["ResourceTagMappingList"])

    return resources


def classify_resources(resources):
    """ARN からリソースの種類ごとに分類する"""
    classified = {
        "lambda": [],
        "s3": [],
        "iam_role": [],
        "iam_policy": [],
        "logs": [],
        "dynamodb": [],
        "apigateway": [],
        "sqs": [],
        "sns": [],
        "events": [],
        "other": [],
    }

    for r in resources:
        arn = r["ResourceARN"]

        if ":lambda:" in arn and ":function:" in arn:
            classified["lambda"].append(arn)
        elif ":s3:::" in arn:
            classified["s3"].append(arn)
        elif ":iam:" in arn and ":role/" in arn:
            classified["iam_role"].append(arn)
        elif ":iam:" in arn and ":policy/" in arn:
            classified["iam_policy"].append(arn)
        elif ":logs:" in arn and ":log-group:" in arn:
            classified["logs"].append(arn)
        elif ":dynamodb:" in arn and ":table/" in arn:
            classified["dynamodb"].append(arn)
        elif ":apigateway:" in arn:
            classified["apigateway"].append(arn)
        elif ":sqs:" in arn:
            classified["sqs"].append(arn)
        elif ":sns:" in arn:
            classified["sns"].append(arn)
        elif ":events:" in arn:
            classified["events"].append(arn)
        else:
            classified["other"].append(arn)

    return classified


# ========== 各リソースの削除処理 ==========

def delete_lambda_functions(arns, dry_run):
    if not arns:
        return
    client = boto3.client("lambda", region_name=REGION)
    for arn in arns:
        func_name = arn.split(":")[-1]
        print_found("Lambda関数", func_name)
        if dry_run:
            continue
        try:
            client.delete_function(FunctionName=func_name)
            print_deleted("Lambda関数", func_name)
        except Exception as e:
            print_error("Lambda関数", func_name, e)


def delete_s3_buckets(arns, dry_run):
    if not arns:
        return
    s3 = boto3.resource("s3", region_name=REGION)
    for arn in arns:
        bucket_name = arn.split(":::")[-1]
        print_found("S3バケット", bucket_name)
        if dry_run:
            continue
        try:
            bucket = s3.Bucket(bucket_name)
            # バケット内の全オブジェクト（バージョニング含む）を削除
            bucket.object_versions.all().delete()
            bucket.objects.all().delete()
            bucket.delete()
            print_deleted("S3バケット", bucket_name)
        except Exception as e:
            print_error("S3バケット", bucket_name, e)


def delete_iam_roles(arns, dry_run):
    if not arns:
        return
    client = boto3.client("iam")
    for arn in arns:
        role_name = arn.split("/")[-1]
        print_found("IAMロール", role_name)
        if dry_run:
            continue
        try:
            # アタッチされたポリシーをデタッチ
            policies = client.list_attached_role_policies(RoleName=role_name)
            for policy in policies["AttachedPolicies"]:
                client.detach_role_policy(
                    RoleName=role_name, PolicyArn=policy["PolicyArn"]
                )

            # インラインポリシーを削除
            inline = client.list_role_policies(RoleName=role_name)
            for policy_name in inline["PolicyNames"]:
                client.delete_role_policy(
                    RoleName=role_name, PolicyName=policy_name
                )

            # ロールを削除
            client.delete_role(RoleName=role_name)
            print_deleted("IAMロール", role_name)
        except Exception as e:
            print_error("IAMロール", role_name, e)


def delete_log_groups(arns, dry_run):
    if not arns:
        return
    client = boto3.client("logs", region_name=REGION)
    for arn in arns:
        # ARN 形式: arn:aws:logs:region:account:log-group:name:*
        log_group = arn.split("log-group:")[-1].rstrip(":*")
        print_found("CloudWatch Logsグループ", log_group)
        if dry_run:
            continue
        try:
            client.delete_log_group(logGroupName=log_group)
            print_deleted("CloudWatch Logsグループ", log_group)
        except Exception as e:
            print_error("CloudWatch Logsグループ", log_group, e)


def delete_dynamodb_tables(arns, dry_run):
    if not arns:
        return
    client = boto3.client("dynamodb", region_name=REGION)
    for arn in arns:
        table_name = arn.split("/")[-1]
        print_found("DynamoDBテーブル", table_name)
        if dry_run:
            continue
        try:
            client.delete_table(TableName=table_name)
            print_deleted("DynamoDBテーブル", table_name)
        except Exception as e:
            print_error("DynamoDBテーブル", table_name, e)


def delete_sqs_queues(arns, dry_run):
    if not arns:
        return
    client = boto3.client("sqs", region_name=REGION)
    for arn in arns:
        queue_name = arn.split(":")[-1]
        print_found("SQSキュー", queue_name)
        if dry_run:
            continue
        try:
            url = client.get_queue_url(QueueName=queue_name)["QueueUrl"]
            client.delete_queue(QueueUrl=url)
            print_deleted("SQSキュー", queue_name)
        except Exception as e:
            print_error("SQSキュー", queue_name, e)


def delete_sns_topics(arns, dry_run):
    if not arns:
        return
    client = boto3.client("sns", region_name=REGION)
    for arn in arns:
        print_found("SNSトピック", arn.split(":")[-1])
        if dry_run:
            continue
        try:
            client.delete_topic(TopicArn=arn)
            print_deleted("SNSトピック", arn.split(":")[-1])
        except Exception as e:
            print_error("SNSトピック", arn.split(":")[-1], e)


def delete_api_gateways(arns, dry_run):
    if not arns:
        return
    client = boto3.client("apigateway", region_name=REGION)
    for arn in arns:
        # API Gateway の ARN からは REST API ID を抽出
        parts = arn.split("/")
        print_found("API Gateway", arn)
        if dry_run:
            continue
        try:
            # REST API の場合
            if "restapis" in arn:
                api_id = parts[parts.index("restapis") + 1]
                client.delete_rest_api(restApiId=api_id)
                print_deleted("API Gateway", api_id)
        except Exception as e:
            print_error("API Gateway", arn, e)


# ========== メイン処理 ==========

def main():
    parser = argparse.ArgumentParser(description="タグ指定で AWS リソースを一括削除")
    parser.add_argument("--key", default=TAG_KEY, help=f"タグキー (デフォルト: {TAG_KEY})")
    parser.add_argument("--value", default=DEFAULT_TAG_VALUE, help=f"タグ値 (デフォルト: {DEFAULT_TAG_VALUE})")
    parser.add_argument("--dry-run", action="store_true", help="削除対象の確認のみ（実際には削除しない）")
    parser.add_argument("--region", default=REGION, help=f"AWSリージョン (デフォルト: {REGION})")
    args = parser.parse_args()

    global REGION
    REGION = args.region

    print_header(f"タグ検索: {args.key} = {args.value}")
    if args.dry_run:
        print(f"  {Color.YELLOW}>>> DRY-RUN モード: 削除は実行しません <<<{Color.END}")

    # 1. タグ付きリソースを検索
    print(f"\n  リソースを検索中...")
    resources = find_tagged_resources(args.key, args.value)

    if not resources:
        print(f"\n  {Color.GREEN}タグ {args.key}={args.value} のリソースは見つかりませんでした。{Color.END}")
        return

    # 2. リソースを種類別に分類
    classified = classify_resources(resources)

    # 3. 検出結果のサマリーを表示
    print_header("検出結果サマリー")
    total = 0
    for rtype, arns in classified.items():
        if arns:
            count = len(arns)
            total += count
            print(f"  {rtype:20s}: {count} 件")
    print(f"  {'─' * 30}")
    print(f"  {'合計':20s}: {total} 件")

    # 未対応リソースの警告
    if classified["other"]:
        print(f"\n  {Color.YELLOW}[注意] 以下のリソースは自動削除に未対応です。手動で削除してください:{Color.END}")
        for arn in classified["other"]:
            print(f"    - {arn}")

    # 4. 削除確認
    if not args.dry_run:
        print_header("削除確認")
        print(f"  {Color.RED}{Color.BOLD}上記 {total} 件のリソースを削除します。この操作は元に戻せません。{Color.END}")
        confirm = input(f"\n  続行しますか？ (yes/no): ").strip().lower()
        if confirm != "yes":
            print(f"\n  {Color.YELLOW}中断しました。{Color.END}")
            return

    # 5. 削除実行（依存関係を考慮した順序）
    print_header("削除処理" if not args.dry_run else "DRY-RUN 結果")

    # API Gateway → Lambda → DynamoDB → SQS → SNS → S3 → Logs → IAM の順で削除
    delete_api_gateways(classified["apigateway"], args.dry_run)
    delete_lambda_functions(classified["lambda"], args.dry_run)
    delete_dynamodb_tables(classified["dynamodb"], args.dry_run)
    delete_sqs_queues(classified["sqs"], args.dry_run)
    delete_sns_topics(classified["sns"], args.dry_run)
    delete_s3_buckets(classified["s3"], args.dry_run)
    delete_log_groups(classified["logs"], args.dry_run)
    delete_iam_roles(classified["iam_role"], args.dry_run)

    if args.dry_run:
        print(f"\n  {Color.CYAN}実際に削除するには --dry-run を外して再実行してください。{Color.END}")
    else:
        print_header("完了")
        print(f"  {Color.GREEN}すべてのリソースの削除が完了しました。{Color.END}")


if __name__ == "__main__":
    main()