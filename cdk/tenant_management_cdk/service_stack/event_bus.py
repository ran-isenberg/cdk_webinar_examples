from pathlib import Path

from aws_cdk import aws_dynamodb
from aws_cdk import aws_events
#from aws_cdk import aws_events_targets
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda
from aws_cdk import aws_lambda_event_sources
from aws_cdk import core

from tenant_management_cdk.service_stack.tenant_env_consts import (
    get_git_root,
    TENANT_MANAGEMENT_SERVICE,
)

# pylint: disable=print-used


# Define a dynamo db stream source lambda which will forward the dynamodb event to an event bus and
# from there to the tenant provision lambda.
class DynamoToEventBridge(core.Construct):

    # pylint: disable=redefined-builtin,invalid-name,no-value-for-parameter
    def __init__(self, scope: core.Construct, id: str, dynamo_table: aws_dynamodb.Table) -> None:
        super().__init__(scope, id)

        if not dynamo_table:
            print('missing dynamo db parameter')
            raise TypeError('missing dynamo db stream arn parameter')

        self._parents_dir: str = get_git_root(Path(__file__))
        self._log_utils_dir: Path = Path(f'{self._parents_dir}/log_utils')
        self._cloudwatch_logs_policy = iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")

        #### eventbridge -> event bus -> rule
        ## lambda puts event to event bus , a rule is triggered -> lambda is called with the event
        ## other destinations are possible

        # create event bus
        event_bus = aws_events.EventBus(scope=self, id=f'{id}TenantMgmtBus', event_bus_name=f'{id}TenantMgmtBus')

        # create lambdas
        self.dispatcher_lambda = self._create_dispatcher_lambda(id, event_bus)

        # trigger a lambda on a DynamoDB change, create an event source
        stream_event_source = aws_lambda_event_sources.DynamoEventSource(table=dynamo_table,
                                                                         starting_position=aws_lambda.StartingPosition.LATEST)
        # bind the event source to a lambda
        stream_event_source.bind(self.dispatcher_lambda)

        # create a rule that triggers when the stream lambda pushes an event to the event bus
        # target is a list of destinations, currently we define a lambda
        #aws_events.Rule(
        #    scope=self,
        #    id=f'{id}DynamoEventRule',
        #    rule_name=f'{id}DynamoEventRule',
        #    targets=[aws_events_targets.LambdaFunction(handler=self.provision_lambda)],
        #    description='tenant management dynamo CRUD destination trigger',
        #    event_bus=event_bus,
        #    event_pattern=aws_events.EventPattern(source=[self.dispatcher_lambda.function_arn]),
        #)

    def _create_dispatcher_lambda(self, id: str, event_bus: aws_events.EventBus) -> None:
        # bind dispatch lambda to dynamo db with an IAM to put events in the event bus
        lambda_role = iam.Role(
            self,
            'TenantMgmtDispatch',
            assumed_by=iam.ServicePrincipal('lambda.amazonaws.com'),
            inline_policies={
                'TenantMgmtDispatchPolicy':
                    iam.PolicyDocument(statements=[
                        iam.PolicyStatement(actions=['events:PutEvents'], resources=[event_bus.event_bus_arn], effect=iam.Effect.ALLOW),
                    ]),
                "TracingPolicy":
                    iam.PolicyDocument(statements=[
                        iam.PolicyStatement(
                            actions=["ssm:Describe*", "ssm:Get*", "ssm:List*"],
                            resources=["arn:aws:ssm:*"],
                            effect=iam.Effect.ALLOW,
                        ),
                    ]),
            },
            managed_policies=[self._cloudwatch_logs_policy],
        )

        return aws_lambda.Function(
            self,
            f'{id}Dispatcher',
            function_name=f'{id}Dispatcher',
            code=aws_lambda.Code.from_asset(".build/tenant_crud_dispatcher"),
            handler='functions.crud_dispatcher.crud_dispatch_dynamodb_source',
            environment={
                'EVENT_BUS_NAME': event_bus.event_bus_name,  # where to put the events into
            },
            runtime=aws_lambda.Runtime.PYTHON_3_7,
            role=lambda_role,
            memory_size=192,
        )
