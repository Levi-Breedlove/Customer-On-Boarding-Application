"Lambda function for unzipping application documents"
import os
import zipfile
import boto3

unzipped_dir = "/tmp/unzipped/"
unzipped_s3_prefix = "unzipped/"
s3 = boto3.client('s3')

def unzip_object(bucket, key):
    """Download zip file, extract, delete the zipped archive from Lambda /tmp storage, and return individual file names"""
    zip_name = os.path.basename(key)
    zip_fullpath = f'/tmp/{zip_name}'
    s3.download_file(bucket, key, zip_fullpath)
    with zipfile.ZipFile(zip_fullpath, 'r') as zip_ref:
        zip_ref.extractall(unzipped_dir)
    os.remove(zip_fullpath)

    zipped_files = os.listdir(unzipped_dir)
    return zipped_files

def lambda_handler(event, context):
    "Unzip application documents and upload to the unzipped prefix"
    bucket = event['detail']['bucket']['name']
    key = event['detail']['object']['key']

    # Unzip the object from the event
    files_list = unzip_object(bucket, key)

    # retrieve app_uuid from zip file
    app_uuid = os.path.basename(key).replace(".zip", "")

    # upload files to the unzipped location
    for file in files_list:
        s3.upload_file(unzipped_dir + file, bucket, unzipped_s3_prefix + file)

    return {
        "app_uuid": app_uuid
    }