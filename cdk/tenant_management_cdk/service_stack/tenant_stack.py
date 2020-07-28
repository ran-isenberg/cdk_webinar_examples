import getpass
import os

from aws_cdk import (core, aws_route53 as route53, aws_route53_targets as route53_targets, aws_certificatemanager as cert_manager)
from aws_cdk.aws_apigateway import EndpointType, DomainName, SecurityPolicy
from aws_cdk.core import Tag, Stack

from tenant_management_cdk.service_stack.event_bus import DynamoToEventBridge
from tenant_management_cdk.service_stack.tenant_env_consts import get_stack_name
from tenant_management_cdk.service_stack.tenant_crud_api import TenantCrudAPI


class TenantStack(core.Stack):

    def __init__(self, scope: core.Construct, id_: str, **kwargs) -> None:
        super().__init__(scope, id_, **kwargs)

        # False positive, see this issue: https://github.com/PyCQA/pylint/issues/3417
        # pylint: disable=no-value-for-parameter
        Tag.add(scope=self, key='owner', value=getpass.getuser())

        # Import user_pool_arn from userPool stack
        profile: str = os.getenv('PROFILE', 'dev')
        stack_name = get_stack_name()

        # create REST API to DynamoDB CRUD contruct
        self.crud_api = TenantCrudAPI(self, f'{stack_name}RestAPI', profile)

        # create DynamoDB to Eventbridge
        self.eventbridge = DynamoToEventBridge(self, f'{stack_name}EventBus', self.crud_api.table)
       