from datetime import date

from botocore.exceptions import ClientError
import boto3

from model.message import Message
from .repository import Repository


class DynamoDB(Repository):
    def __init__(self, table_name, endpoint_url=None):
        self.dynamodb = boto3.resource("dynamodb", endpoint_url=endpoint_url)
        self.table_name = table_name
        self.table = self.dynamodb.Table(table_name)
        self.cache = {}

    def get_message(self, target_date: date) -> Message:
        str_date = target_date.strftime("%Y/%m/%d")
        try:
            response = self.table.get_item(Key={"Date": str_date})
        except ClientError as e:
            print(e.response["Error"]["Message"])
            raise e
        else:
            if "Item" in response:
                return Message(date=target_date, message=response["Item"]["Message"])
        return None
