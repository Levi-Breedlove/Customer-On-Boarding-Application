"Process license validation requests"
import os
import json
import requests
import boto3
from aws_lambda_powertools import Tracer

url = os.environ['INVOKE_URL']
env_table = os.environ['TABLE']
env_topic = os.environ['TOPIC']
env_queue_url = os.environ['QUEUE_URL']
tracer = Tracer()

dynamodb = boto3.resource('dynamodb')
ddb_table = dynamodb.Table(env_table)
sns = boto3.client('sns')
sqs = boto3.client('sqs')

@tracer.capture_lambda_handler
def lambda_handler(event, _):
    "Process queue events: call API and update Dynamo table"

    records = event['Records']
    for record in records:
        payload = json.loads(record['body'])
        uuid = payload.pop('app_uuid')
        r = requests.post(url, json=payload)
        api_response = r.json()

        # Update DDB, send SNS, and move files based on license validation
        ddb_table.update_item(
                Key={
                    'APP_UUID': uuid
                    },
                UpdateExpression='SET LICENSE_VALIDATION = :v_match',
                ExpressionAttributeValues={
                    ':v_match': api_response
                    }
                )

        if not api_response:
            sns.publish(
                TopicArn= env_topic,
                Message= 'License validation by 3rd party FAILED',
                Subject='License validation by 3rd party FAILED',
                )