import os
import tempfile

import pdfkit

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
        s3_endpoint=None,
        minio_user=None,
        minio_password=None,
        wkhtmltopdf_path=None,
    ):
        self.s3_endpoint = self.or_none(s3_endpoint)
        self.minio_user = self.or_none(minio_user)
        self.minio_password = self.or_none(minio_password)
        self.wkhtmltopdf_path = self.or_none(wkhtmltopdf_path)


def html_to_pdf(storage: Storage, object_name, out_dir, config: Config):
    html_path = storage.download_file(object_name, out_dir)

    pdf_path = os.path.join(
        out_dir, os.path.splitext(os.path.basename(object_name))[0] + ".pdf"
    )
    options = {
        "enable-local-file-access": None,
        "header-right": "Simple Serverless Batch",
        "footer-right": "[page]/[topage]",
    }
    pdfkit_config = None
    if config.wkhtmltopdf_path:
        pdfkit_config = pdfkit.configuration(wkhtmltopdf=config.wkhtmltopdf_path)
    pdfkit.from_file(html_path, pdf_path, options=options, configuration=pdfkit_config)

    pdf_object_name = storage.upload_file(pdf_path, os.path.basename(pdf_path))
    return pdf_object_name


def get_storage(config: Config, bucket_name: str) -> Storage:
    if config.s3_endpoint == "":
        return S3(config.bucket_name)
    else:
        return Minio(
            bucket_name,
            endpoint_url=config.s3_endpoint,
            access_key_id=config.minio_user,
            secret_access_key=config.minio_password,
        )


def lambda_handler(event, context):
    config = Config(
        s3_endpoint=os.environ.get("SSB_S3_ENDPOINT"),
        minio_user=os.environ.get("SSB_MINIO_USER"),
        minio_password=os.environ.get("SSB_MINIO_PASSWORD"),
        wkhtmltopdf_path=os.environ.get("SSB_WKHTMLTOPDF_PATH"),
    )

    bucket_name = event["BucketName"]
    html_object_name = event["ObjectName"]
    storage = get_storage(config, bucket_name)

    with tempfile.TemporaryDirectory() as temp_dir:
        pdf_object_name = html_to_pdf(storage, html_object_name, temp_dir, config)
        return {
            "BucketName": bucket_name,
            "ObjectName": pdf_object_name,
        }
