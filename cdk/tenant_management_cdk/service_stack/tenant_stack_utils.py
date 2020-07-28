import getpass
from typing import Any

import boto3


def get_stack_resource(stack_name, resource_name, required: bool = True) -> Any:
    cloudformation = boto3.client('cloudformation')
    response = cloudformation.describe_stacks(StackName=stack_name)
    if response is None or response['Stacks'] is None:
        return None
    outputs = response['Stacks'][0]['Outputs']
    for output in outputs:
        if str(output['OutputKey']) == resource_name:
            return output['OutputValue']

    if required:
        raise AttributeError(f'get_stack_resource() - AttributeError: parameter not found for: '
                             f'stack_name:[{stack_name}], resource_name:[{resource_name}]'
                             f', cannot be null when this method is being called with required=True')
    return None

