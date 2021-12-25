from .s3 import S3


class Minio(S3):
    def __init__(
        self,
        bucket_name: str,
        endpoint_url: str = None,
        access_key_id: str = None,
        secret_access_key: str = None,
    ) -> None:
        super().__init__(
            bucket_name,
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
        )
