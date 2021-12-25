from time import sleep
from typing import Dict, List
from unittest import TestCase
from uuid import uuid4
import json
import logging
import os

from botocore.client import BaseClient
import boto3
import botocore


"""
Make sure env variable AWS_SAM_STACK_NAME exists with the name of the stack we are going to test.
"""


class TestStateMachine(TestCase):
    dummy_message: str
    event_rule_name: str
    state_machine_arn: str
    transaction_table_name: str

    bucket_name: str
    client: BaseClient
    objects_to_delete: List[str] = []

    def assert_object_exists(self, bucket_name: str, key: str):
        client = boto3.client("s3")
        try:
            client.head_object(
                Bucket=bucket_name,
                Key=key,
            )
        except botocore.exceptions.ClientError as e:
            if e.response["Error"]["Code"] == "404":
                raise Exception(
                    f"There is no object named '{key}' in s3 bucket '{self.bucket_name}': {e}"
                )
            else:
                raise Exception(f"Something wrong with this request: {e}")
        except Exception as e:
            raise Exception(f"{e}")

    def put_item_for_test(self) -> dict:
        client = boto3.client("dynamodb")
        return client.put_item(
            TableName="Messages",
            Item={
                "Date": {"S": "2021/11/28"},
                "Message": {"S": self.dummy_message},
            },
        )

    def delete_item_from_dynamodb_table(self):
        client = boto3.client("dynamodb")
        return client.delete_item(
            TableName="Messages",
            Key={
                "Date": {"S": "2021/11/28"},
            },
        )

    def reserve_deleting_object(self, key: str):
        self.objects_to_delete.append(key)

    def delete_objects_from_s3_bucket(self):
        client = boto3.client("s3")
        client.delete_objects(
            Bucket=self.bucket_name,
            Delete={
                "Objects": [{"Key": k} for k in self.objects_to_delete],
            },
        )

    @classmethod
    def get_and_verify_stack_name(cls) -> str:
        stack_name = os.environ.get("AWS_SAM_STACK_NAME")
        if not stack_name:
            raise Exception(
                "Cannot find env var AWS_SAM_STACK_NAME. \n"
                "Please setup this environment variable with the stack name where we are running integration tests."
            )

        # Verify stack exists
        client = boto3.client("cloudformation")
        try:
            client.describe_stacks(StackName=stack_name)
        except Exception as e:
            raise Exception(
                f"Cannot find stack {stack_name}. \n"
                f'Please make sure stack with the name "{stack_name}" exists.'
            ) from e

        return stack_name

    @classmethod
    def _retrieve_resource_by_logical_resource_id(
        cls, resources: List[Dict], logical_resource_id: str
    ) -> List[Dict]:
        return [
            resource
            for resource in resources
            if resource["LogicalResourceId"] == logical_resource_id
        ]

    @classmethod
    def collect_resources(cls) -> None:
        stack_name = "simple-serverless-batch"
        client = boto3.client("cloudformation")

        response = client.list_stack_resources(StackName=stack_name)
        resources = response["StackResourceSummaries"]

        state_machine_resources = cls._retrieve_resource_by_logical_resource_id(
            resources, "MakeReportStateMachine"
        )
        if not state_machine_resources:
            raise Exception("Cannot find MakeReportStateMachine.")

        messages_table_resources = cls._retrieve_resource_by_logical_resource_id(
            resources, "MessagesTable"
        )
        if not messages_table_resources:
            raise Exception("Cannot find MessagesTable.")

        event_rule_resources = cls._retrieve_resource_by_logical_resource_id(
            resources, "CallStateMachine"
        )
        if not event_rule_resources:
            raise Exception("Cannot find CallStateMachine.")

        cls.state_machine_arn = state_machine_resources[0]["PhysicalResourceId"]
        cls.messages_table_name = messages_table_resources[0]["PhysicalResourceId"]
        cls.event_rule_name = event_rule_resources[0]["PhysicalResourceId"]

        response = client.describe_stacks(StackName=stack_name)
        bucket_name_param = [
            p
            for p in response["Stacks"][0]["Parameters"]
            if p["ParameterKey"] == "S3BucketName"
        ]
        if not bucket_name_param:
            raise Exception("Cannot find parameter named S3BucketName")
        cls.bucket_name = bucket_name_param[0]["ParameterValue"]

    @classmethod
    def setUpClass(cls) -> None:
        cls.collect_resources()

    def setUp(self) -> None:
        self.client = boto3.client("stepfunctions")
        self.dummy_message = str(uuid4())
        self.put_item_for_test()

    def tearDown(self) -> None:
        self.delete_item_from_dynamodb_table()
        self.delete_objects_from_s3_bucket()

    def _verify_event_rule(self) -> None:
        client = boto3.client("events")
        rule = client.describe_rule(Name=self.event_rule_name)
        self.assertEqual(
            rule["ScheduleExpression"],
            "cron(0 10 ? * MON-FRI *)",
            "This schedule does not follow the specifications.",
        )
        self.assertEqual(
            rule["State"],
            "ENABLED",
            "This rule must be enabled.",
        )

        response = client.list_targets_by_rule(Rule=self.event_rule_name)
        self.assertEqual(
            response["Targets"][0]["Arn"],
            self.state_machine_arn,
            "The StateMachine is not called by this rule.",
        )

    def _start_execute(self) -> str:
        """
        Start the state machine execution request and record the execution ARN
        """
        response = self.client.start_execution(
            stateMachineArn=self.state_machine_arn,
            name=f"integ-test-{uuid4()}",
            input="{}",
        )
        return response["executionArn"]

    def _wait_execution(self, execution_arn: str):
        while True:
            response = self.client.describe_execution(executionArn=execution_arn)
            status = response["status"]
            if status == "SUCCEEDED":
                logging.info(f"Execution {execution_arn} completely successfully.")
                break
            elif status == "RUNNING":
                logging.info(f"Execution {execution_arn} is still running, waiting")
                sleep(3)
            else:
                self.fail(f"Execution {execution_arn} failed with status {status}")

    def _retrieve_convert_html_to_pdf_input(self, execution_arn: str) -> Dict:
        response = self.client.get_execution_history(executionArn=execution_arn)
        events = response["events"]
        convert_html_to_pdf_entered_event = [
            event
            for event in events
            if event["type"] == "TaskStateEntered"
            and event["stateEnteredEventDetails"]["name"] == "Convert Html to Pdf"
        ]

        input = json.loads(
            convert_html_to_pdf_entered_event[0]["stateEnteredEventDetails"]["input"]
        )
        self.reserve_deleting_object(input["ObjectName"])
        return input

    def _retrieve_convert_html_to_pdf_output(self, execution_arn: str) -> Dict:
        response = self.client.get_execution_history(executionArn=execution_arn)
        events = response["events"]
        convert_html_to_pdf_entered_event = [
            event
            for event in events
            if event["type"] == "TaskStateExited"
            and event["stateExitedEventDetails"]["name"] == "Convert Html to Pdf"
        ]

        output = json.loads(
            convert_html_to_pdf_entered_event[0]["stateExitedEventDetails"]["output"]
        )
        self.reserve_deleting_object(output["ObjectName"])
        return output

    def _verify_convert_html_to_pdf_input(self, input: Dict) -> None:
        expected_object_name = "2021_11_28.html"
        self.assertDictEqual(
            input,
            {
                "BucketName": self.bucket_name,
                "ObjectName": expected_object_name,
            },
        )
        self.assert_object_exists(self.bucket_name, expected_object_name)

    def _verify_convert_html_to_pdf_output(self, output: Dict) -> None:
        expected_object_name = "2021_11_28.pdf"
        self.assertDictEqual(
            output,
            {
                "BucketName": self.bucket_name,
                "ObjectName": expected_object_name,
            },
        )
        self.assert_object_exists(self.bucket_name, expected_object_name)

    def test_state_machine(self):
        self._verify_event_rule()
        execution_arn = self._start_execute()
        self._wait_execution(execution_arn)
        input = self._retrieve_convert_html_to_pdf_input(execution_arn)
        self._verify_convert_html_to_pdf_input(input)
        output = self._retrieve_convert_html_to_pdf_output(execution_arn)
        self._verify_convert_html_to_pdf_output(output)
