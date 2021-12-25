from typing import Dict
import os
import uuid

from storage.s3 import S3


def configure_mock(mocker, config={}) -> Dict:
    mock_bucket = mocker.MagicMock()
    default = {
        "upload_file.return_value": True,
        "download_file.return_value": True,
    }
    if "Bucket" in config:
        default.update(config["Bucket"])
    mock_bucket.configure_mock(**default)
    mock_s3 = mocker.MagicMock()
    default = {
        "Bucket.return_value": mock_bucket,
    }
    if "S3" in config:
        default.update(config["S3"])
    mock_s3.configure_mock(**default)
    mocker.patch("boto3.resource", return_value=mock_s3)

    return {
        "Bucket": mock_bucket,
        "S3": mock_s3,
    }


def test_upload_file(mocker):
    mock_bucket = configure_mock(mocker)["Bucket"]
    file_path = str(uuid.uuid4())
    object_name = str(uuid.uuid4())
    s3 = S3("some_bucket")

    result = s3.upload_file(file_path, object_name)
    assert result == object_name
    mock_bucket.upload_file.assert_called_with(file_path, object_name)


def test_download_file(mocker):
    mock_bucket = configure_mock(mocker)["Bucket"]
    dist_dir = os.path.join("tmp", "download")
    object_name = "11_28.html"
    expected_path = os.path.join("tmp", "download", "11_28.html")
    s3 = S3("some_bucket")

    result = s3.download_file(object_name, dist_dir)
    assert result == expected_path
    mock_bucket.download_file.assert_called_with(object_name, expected_path)
