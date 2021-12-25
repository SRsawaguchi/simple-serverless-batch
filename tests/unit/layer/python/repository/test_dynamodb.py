import datetime

import pytest

from repository.dynamodb import DynamoDB


def configure_mock(mocker, mock_table_config_override={}):
    mock_db = mocker.MagicMock()
    mock_table = mocker.MagicMock()
    mock_table.configure_mock(
        **{
            "get_item.return_value": mock_table_config_override.get(
                "get_item.return_value", {"Item": {"Attribute": True}}
            ),
        }
    )
    mock_db.configure_mock(
        **{
            "Table.return_value": mock_table,
        }
    )
    mocker.patch("boto3.resource", return_value=mock_db)

    return {
        "mock_db": mock_db,
        "mock_table": mock_table,
    }


@pytest.fixture()
def message():
    return {
        "Date": "2021/11/28",
        "Message": "Hello, world!!",
    }


def test_get_message(message, mocker):
    mock_table = configure_mock(
        mocker,
        mock_table_config_override={
            "get_item.return_value": {"Item": message},
        },
    )["mock_table"]
    db = DynamoDB("some_table")

    target_date = datetime.datetime.strptime(message["Date"], "%Y/%m/%d")
    result = db.get_message(target_date)
    mock_table.get_item.assert_called_with(Key={"Date": message["Date"]})
    assert result.date == target_date
    assert result.message == message["Message"]
