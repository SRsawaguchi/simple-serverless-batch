import datetime
import os
import tempfile

from botocore.exceptions import ClientError
import boto3
import pystache


class Config:
    @staticmethod
    def or_none(val):
        is_empty = val is None or val == ""
        return None if is_empty else val

    def __init__(
        self,
        bucket_name,
        dynamodb_table_name,
        s3_endpoint=None,
        dynamodb_endpoint=None,
        minio_user=None,
        minio_password=None,
    ):
        self.bucket_name = bucket_name
        self.dynamodb_table_name = dynamodb_table_name
        self.s3_endpoint = self.or_none(s3_endpoint)
        self.dynamodb_endpoint = self.or_none(dynamodb_endpoint)
        self.minio_user = self.or_none(minio_user)
        self.minio_password = self.or_none(minio_password)


def get_target_date():
    return datetime.date(2021, 11, 28)


def upload_file(bucket_name, file_path, object_name, **kwargs):
    s3 = boto3.resource("s3", **kwargs)
    bucket = s3.Bucket(bucket_name)
    bucket.upload_file(file_path, object_name)
    return object_name


def get_message(target_date, table_name, endpoint_url=None):
    dynamodb = boto3.resource("dynamodb", endpoint_url=endpoint_url)
    table = dynamodb.Table(table_name)
    str_date = target_date.strftime("%Y/%m/%d")
    try:
        response = table.get_item(Key={"Date": str_date})
    except ClientError as e:
        print(e.response["Error"]["Message"])
        raise e
    else:
        if "Item" in response:
            return response["Item"]["Message"]
    return None


def get_object_name(target_date: datetime.date, ext=".html"):
    str_date = target_date.strftime("%Y_%m_%d")
    return f"{str_date}{ext}"


def make_report(target_date, out_dir, config: Config):
    template = """
<!DOCTYPE html>
<html>
    <head>
        <meta charset="UTF-8">
        <title>Message</title>
    </head>
    <body>
        {{{ message }}}
    </body>
</html>
"""
    msg = get_message(target_date, config.dynamodb_table_name, config.dynamodb_endpoint)
    html = pystache.render(template, {"message": msg})

    object_name = get_object_name(target_date)
    html_path = os.path.join(out_dir, os.path.basename(object_name))
    with open(html_path, mode="w") as f:
        f.write(html)

    upload_file(
        config.bucket_name,
        html_path,
        object_name,
        endpoint_url=config.s3_endpoint,
        aws_access_key_id=config.minio_user,
        aws_secret_access_key=config.minio_password,
    )
    return object_name


def lambda_handler(event, context):
    config = Config(
        bucket_name=os.environ.get("SSB_BUCKET_NAME"),
        dynamodb_table_name=os.environ.get("SSB_DYNAMODB_TABLE_NAME"),
        s3_endpoint=os.environ.get("SSB_S3_ENDPOINT"),
        dynamodb_endpoint=os.environ.get("SSB_DYNAMODB_ENDPOINT"),
        minio_user=os.environ.get("SSB_MINIO_USER"),
        minio_password=os.environ.get("SSB_MINIO_PASSWORD"),
    )

    with tempfile.TemporaryDirectory() as temp_dir:
        object_name = make_report(get_target_date(), temp_dir, config)
        return {
            "BucketName": config.bucket_name,
            "ObjectName": object_name,
        }
