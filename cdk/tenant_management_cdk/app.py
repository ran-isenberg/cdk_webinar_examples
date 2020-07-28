#!/usr/bin/env python3
#pylint: disable=invalid-name
from boto3 import session, client
import os

from aws_cdk.core import App, Environment
from tenant_management_cdk.service_stack.tenant_env_consts import get_stack_name
from tenant_management_cdk.service_stack.tenant_stack import TenantStack

region = session.Session().region_name
account = client('sts').get_caller_identity()['Account']

app = App()
tenants_stack = TenantStack(
    app, get_stack_name(),
    env=Environment(account=os.environ.get("AWS_DEFAULT_ACCOUNT", account), region=os.environ.get("AWS_DEFAULT_REGION", region)))

## When we run this file it will
## transform the code into a CFN template
app.synth()
