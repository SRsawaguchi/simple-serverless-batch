import datetime
import os
import tempfile

import pystache

from repository.dynamodb import DynamoDB
from repository.repository import Repository
from storage.minio import Minio
from storage.s3 import S3
from storage.storage import Storage


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


def get_object_name(target_date: datetime.date, ext=".html"):
    str_date = target_date.strftime("%Y_%m_%d")
    return f"{str_date}{ext}"


def make_report(repo: Repository, storage: Storage, target_date, out_dir):
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
    msg = repo.get_message(target_date)
    html = pystache.render(template, {"message": msg.message})

    object_name = get_object_name(target_date)
    html_path = os.path.join(out_dir, os.path.basename(object_name))
    with open(html_path, mode="w") as f:
        f.write(html)

    storage.upload_file(html_path, object_name)
    return object_name


def get_repository(config: Config) -> Repository:
    return DynamoDB(config.dynamodb_table_name, endpoint_url=config.dynamodb_endpoint)


def get_storage(config: Config) -> Storage:
    if config.s3_endpoint == "":
        return S3(config.bucket_name)
    else:
        return Minio(
            config.bucket_name,
            endpoint_url=config.s3_endpoint,
            access_key_id=config.minio_user,
            secret_access_key=config.minio_password,
        )


def lambda_handler(event, context):
    config = Config(
        bucket_name=os.environ.get("SSB_BUCKET_NAME"),
        dynamodb_table_name=os.environ.get("SSB_DYNAMODB_TABLE_NAME"),
        s3_endpoint=os.environ.get("SSB_S3_ENDPOINT"),
        dynamodb_endpoint=os.environ.get("SSB_DYNAMODB_ENDPOINT"),
        minio_user=os.environ.get("SSB_MINIO_USER"),
        minio_password=os.environ.get("SSB_MINIO_PASSWORD"),
    )

    repo = get_repository(config)
    storage = get_storage(config)

    with tempfile.TemporaryDirectory() as temp_dir:
        object_name = make_report(repo, storage, get_target_date(), temp_dir)
        return {
            "BucketName": config.bucket_name,
            "ObjectName": object_name,
        }
