"""
    AWS Lambda resource tagger for new Amazon EC2 instances.

    Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
    SPDX-License-Identifier: MIT-0

    Amazon EventBridge triggers this AWS Lambda function when new EC2 joins the AWS resource group. 
    Then this Lambda function apply tags defined in the function to the EC2 instances newly joined the AWS Resource group.
"""

import json
import logging

import boto3
import botocore

import re

logging.getLogger().setLevel(logging.INFO)
log = logging.getLogger(__name__)

# Instantiate Boto3 clients & resources for every AWS service API called
ec2_client = boto3.client("ec2")
ec2_resource = boto3.resource("ec2")

# Apply resource tags to EC2 instances & attached EBS volumes
def set_ec2_instance_attached_tags(ec2_instance_id, resource_tags):
    """Applies a list of passed resource tags to the Amazon EC2 instance.
    Args:
        ec2_instance_id: EC2 instance identifier
        resource_tags: a list of key:string,value:string resource tag dictionaries
    Returns:
        Returns True if tag application successful and False if not
    Raises:
        AWS Python API "Boto3" returned client errors
    """
    try:
        response = ec2_client.create_tags(
            Resources=[ec2_instance_id], Tags=resource_tags
        )
    except botocore.exceptions.ClientError as error:
        log.error(f"Boto3 API returned error: {error}")
        log.error(f"No Tags Applied To: {ec2_instance_id}")
        return False

def event_parser(event):
    """Extract list of new EC2 instances from the event

    Args:
        event: an Eventbridge event in python dictionary format

    Returns a dictionary containing these keys and their values:
        resource_group_name: the name of resource group 
        instances_set: list of EC2 instances & parameter dictionaries

    Raises:
        none
    """
    returned_event_fields = {}
    
    # Extract & return the list of new EC2 instance(s) and their parameters
    returned_event_fields["instances_set"] = (
        event.get("detail").get("resources")
    )
  
    return returned_event_fields


def lambda_handler(event, context):
    resource_tags = [{"Key": "Project", "Value": "RG_Lifecycle"}]

    # Parse the passed event and extract pertinent EC2s
    event_fields = event_parser(event)

    resource_tags.append(
            {"Key": "Resource_Group", "Value": event.get("detail").get("group").get("name")}
        )
        
    # Tag EC2 instances listed in the event
    for item in event_fields.get("instances_set"):
        if item.get("membership-change") == "add":
            ec2_instance_arn = item.get("arn")
            ec2_instance_id = re.search('/(.+)', ec2_instance_arn)
            ec2_instance_id= ec2_instance_id.group(1)

            if set_ec2_instance_attached_tags(ec2_instance_id, resource_tags):
                log.info("'statusCode': 200")
                log.info(f"'Resource ID': {ec2_instance_id}")
                log.info(f"'body': {json.dumps(resource_tags)}")

            else:
                log.info("'statusCode': 500")
                log.info(f"'No tags applied to Resource ID': {ec2_instance_arn}")
                log.info(f"'Lambda function name': {context.function_name}")
        else:
            log.info(f"'No newly added Amazon EC2 to tag': 'Event ID: {event.get('id')}'")
