from typing import Any
import os

import boto3

from .storage import Storage


class S3(Storage):
    bucket_name: str
    s3: Any
    bucket: Any

    def __init__(self, bucket_name: str, **kwargs) -> None:
        super().__init__()
        self.s3 = boto3.resource("s3", **kwargs)
        self.bucket = self.s3.Bucket(bucket_name)
        self.bucket_name = bucket_name

    def upload_file(self, file_path: str, object_name: str) -> str:
        self.bucket.upload_file(file_path, object_name)
        return object_name

    def download_file(self, object_name: str, dist_dir: str) -> str:
        object_path = os.path.join(dist_dir, os.path.basename(object_name))
        self.bucket.download_file(object_name, object_path)
        return object_path
