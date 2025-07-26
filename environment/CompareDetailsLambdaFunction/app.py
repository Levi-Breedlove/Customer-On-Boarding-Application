"Compare the details extracted from the license and the CSV file"
import csv
import os
import boto3
from aws_lambda_powertools import Tracer 

env_table = os.environ['TABLE']
env_topic = os.environ['TOPIC']
tracer = Tracer() 

s3 = boto3.client('s3')
unzipped_s3_prefix = "unzipped/"
dynamodb = boto3.resource('dynamodb')
ddb_table = dynamodb.Table(env_table)
textract = boto3.client('textract')
sns = boto3.client('sns')


def textract_response(bucket, license_key):
    "Send license to textract"

    # Pass the license image to textract to extract information
    print("Starting license analysis")
    response = textract.analyze_id(
        DocumentPages=[{
                'S3Object': {
                'Bucket': bucket,
                'Name': license_key
            }
        }]
    )

    id_document = response['IdentityDocuments'][0]
    id_data = id_document['IdentityDocumentFields']
    id_fields = {}

    # Build dictionary of the CSV fields and textract values
    csv_fields = ['DOCUMENT_NUMBER','FIRST_NAME','LAST_NAME','DATE_OF_BIRTH',
                    'ADDRESS','STATE_IN_ADDRESS','CITY_IN_ADDRESS','ZIP_CODE_IN_ADDRESS']
    id_fields = { field['Type']['Text']: field['ValueDetection']['Text'] for field in id_data
                 if field['Type']['Text'] in csv_fields }
    print("finished textract")
    return id_fields


def compare_dictionaries(app_uuid, details_dict, textract_dict):
    "Compare license and csv"
    print("Comparing license and csv")

    comparison = details_dict == textract_dict

    # Update DDB with license data match value, SNS publish
    ddb_table.update_item(
        Key={
            'APP_UUID': app_uuid
            },
        UpdateExpression='SET LICENSE_DETAILS_MATCH = :d_match',
        ExpressionAttributeValues={
            ':d_match': comparison
            }
        )

    if not comparison:
        sns.publish(
            TopicArn= env_topic,
            Message= 'Data validation between license and CSV FAILED',
            Subject='Data validation between license and CSV FAILED',
            )
        raise ValueError('Data comparison between App and license FAILED. Program will stop')

    return comparison
@tracer.capture_lambda_handler   
def lambda_handler(event, context):
    "Download the CSV, send the license to textract and compare"
    bucket = event['detail']['bucket']['name']
    app_uuid = event["application"]["app_uuid"]
    details_key = f"{unzipped_s3_prefix}{app_uuid}_details.csv"
    details_file = f"/tmp/{app_uuid}_details.csv"
    license_key = f"{unzipped_s3_prefix}{app_uuid}_license.png"

    s3.download_file(bucket, details_key, details_file)

    with open(details_file, 'r', encoding="utf-8") as file:
        reader = csv.DictReader(file)
        details_dict = next(reader)

    # Submit license to Textract to extract fields
    textract_dict = textract_response(bucket, license_key)

    # Compare the Textract fields with the CSV file
    compare_dictionaries(app_uuid, details_dict, textract_dict)

    return True