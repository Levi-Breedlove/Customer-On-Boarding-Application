"Fake driver license API responds with the validation_override"
import json

def lambda_handler(event, context):
    "Takes API gateway event and responds with the validation_override"
    body = event['body']
    body_json = json.loads(body)
    license_id = body_json['driver_license_id']
    override_parameter = body_json['validation_override']

    response = {}
    response['statusCode'] = 200
    response['body'] = override_parameter
    return response