import os
import io
import boto3
import json
import csv
import logging
logger = logging.getLogger(__name__)
logging.getLogger().setLevel(logging.INFO)

# grab environment variables
ENDPOINT_NAME = os.environ['ENDPOINT_NAME']
runtime= boto3.client('runtime.sagemaker')

def lambda_handler(event, context):
    logger.info('Endpoint Name %s' % ENDPOINT_NAME)
    logger.info ("Received event: " + json.dumps(event, indent=2))
    data = json.loads(json.dumps(event))
    payload = data['data']
    logger.info('Received Payload %s' % payload)
    response = runtime.invoke_endpoint(EndpointName=ENDPOINT_NAME,
                                       ContentType='text/csv',
                                       Body=payload)
    logger.info('Returned Response %s' % response)
    result = response['Body'].read()
    logger.info('Result from Post %s' % result)
    predicted_label = result
    logger.info('Predicted Label %s' % predicted_label)
    return predicted_label
