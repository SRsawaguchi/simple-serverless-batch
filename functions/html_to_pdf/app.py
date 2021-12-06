import os
import tempfile

import boto3
import pdfkit


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


def download_file(bucket_name, object_name, dist_dir, **kwargs):
    s3 = boto3.resource("s3", **kwargs)
    bucket = s3.Bucket(bucket_name)
    object_path = os.path.join(dist_dir, os.path.basename(object_name))
    bucket.download_file(object_name, object_path)
    return object_path


def upload_file(bucket_name, file_path, object_name, **kwargs):
    s3 = boto3.resource("s3", **kwargs)
    bucket = s3.Bucket(bucket_name)
    bucket.upload_file(file_path, object_name)
    return object_name


def html_to_pdf(bucket_name, object_name, out_dir, config: Config):
    html_path = download_file(
        bucket_name,
        object_name,
        out_dir,
        endpoint_url=config.s3_endpoint,
        aws_access_key_id=config.minio_user,
        aws_secret_access_key=config.minio_password,
    )
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

    pdf_object_name = upload_file(
        bucket_name,
        pdf_path,
        os.path.basename(pdf_path),
        endpoint_url=config.s3_endpoint,
        aws_access_key_id=config.minio_user,
        aws_secret_access_key=config.minio_password,
    )
    return pdf_object_name


def lambda_handler(event, context):
    config = Config(
        s3_endpoint=os.environ.get("SSB_S3_ENDPOINT"),
        minio_user=os.environ.get("SSB_MINIO_USER"),
        minio_password=os.environ.get("SSB_MINIO_PASSWORD"),
        wkhtmltopdf_path=os.environ.get("SSB_WKHTMLTOPDF_PATH"),
    )
    bucket_name = event["BucketName"]
    html_object_name = event["ObjectName"]

    with tempfile.TemporaryDirectory() as temp_dir:
        pdf_object_name = html_to_pdf(bucket_name, html_object_name, temp_dir, config)
        return {
            "BucketName": bucket_name,
            "ObjectName": pdf_object_name,
        }
