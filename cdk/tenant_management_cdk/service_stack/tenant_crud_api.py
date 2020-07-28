import getpass

from aws_cdk import (aws_dynamodb, core, aws_iam, aws_apigateway, aws_lambda)

from tenant_management_cdk.service_stack.tenant_env_consts import TENANT_MANAGEMENT_SERVICE
from tenant_management_cdk.service_stack.tenant_stack_utils import get_stack_resource
from tenant_management_cdk.service_stack.user_pool_stack_utils import get_user_pool_stack_name

# pylint: disable=no-value-for-parameter


class TenantCrudAPI(core.Construct):
    _API_GW_NAME = 'TenantMgmtApiGw'
    _TABLE_NAME = 'TenantManagementTable'

    def __init__(self, scope: core.Construct, id_: str, profile: str) -> None:
        super().__init__(scope, id_)
        self._profile = profile
        self._username = getpass.getuser().capitalize()

        # define DynamoDB table with streams
        self.table = aws_dynamodb.Table(
            self,
            TenantCrudAPI._TABLE_NAME,
            partition_key=aws_dynamodb.Attribute(name="id", type=aws_dynamodb.AttributeType.STRING),
            billing_mode=aws_dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=core.RemovalPolicy.DESTROY,
            stream=aws_dynamodb.StreamViewType.NEW_AND_OLD_IMAGES,
        )

        # add table name to stack outputs
        table_output = core.CfnOutput(self, id="TenantsTableName", value=self.table.table_name)
        table_output.override_logical_id("TenantsTableName")

        # define API GW
        self.rest_api: aws_apigateway.LambdaRestApi = aws_apigateway.RestApi(self, "tenant-mgmt-rest-api",
                                                                             rest_api_name="Tenant Management Rest API",
                                                                             description="This service handles tenant managemnet")

        # create congnito authorizer
        self.user_pool_arn = get_stack_resource(get_user_pool_stack_name(), 'TenantManagementUserPoolArn', True)
        self.api_authorizer: aws_apigateway.CfnAuthorizer = aws_apigateway.CfnAuthorizer(
            scope=self,
            name="TenantMgmtApiAuth",
            id="TenantMgmtApiAuth",
            type="COGNITO_USER_POOLS",
            provider_arns=[self.user_pool_arn],
            rest_api_id=self.rest_api.rest_api_id,
            identity_source="method.request.header.Authorization",
        )

        default_cors_preflight_options = {
            "allow_headers": aws_apigateway.Cors.DEFAULT_HEADERS,
            "allow_origins": aws_apigateway.Cors.ALL_ORIGINS
        }

        # add API GW - create "{domain}/tenants"
        self.tenants_resource: aws_apigateway.Resource = self.rest_api.root.add_resource(
            "tenants", default_cors_preflight_options=default_cors_preflight_options)

        # add API GW /tenants/{tenant_id} path
        self.tenant_id_resource = self.tenants_resource.add_resource("{tenant_id}",
                                                                     default_cors_preflight_options=default_cors_preflight_options)
        # add API GW endpoint to outputs
        endpoint_output = core.CfnOutput(self, id=self._API_GW_NAME, value=self.rest_api.url)
        endpoint_output.override_logical_id(self._API_GW_NAME)

        # create REST API Lambdas
        self._create_func = self._add_create_lambda_integration(id_, self.table)
        self._list_func = self._add_list_lambda_integration(id_, self.table)
        self._get_func = self._add_get_lambda_integration(id_, self.table)

    def _add_create_lambda_integration(self, id_: str, table: aws_dynamodb.Table) -> aws_lambda.Function:
        lambda_role = self._create_lambda_role(role_name='TenantCreateRole', table=table, write_permission=True)
        func = aws_lambda.Function(
            self,
            f'{id_}CreateTenant',
            function_name=f'{id_}CreateTenant',
            runtime=aws_lambda.Runtime.PYTHON_3_7,
            code=aws_lambda.Code.from_asset('.build/service'),
            handler='crud_api.functions.handler.create_tenant',
            role=lambda_role,
            environment={
                'TENANT_MNGT_USER_POOL_ARN': self.user_pool_arn,
                'PROFILE': self._profile,
                'USER_NAME': self._username,
                'TENANTS_TABLE_NAME': table.table_name,
            },
            timeout=core.Duration.seconds(10),
            memory_size=192,
        )
        # Bind POST /tenants/ to the lambda
        method = self.tenants_resource.add_method(
            http_method="POST",
            integration=aws_apigateway.LambdaIntegration(handler=func),  # POST /tenants/
            authorization_type=aws_apigateway.AuthorizationType.COGNITO,
        )

        method_resource: aws_apigateway.Resource = method.node.find_child("Resource")
        method_resource.add_property_override("AuthorizerId", {"Ref": self.api_authorizer.logical_id})
        return func

    def _add_list_lambda_integration(self, id_: str, table: aws_dynamodb.Table) -> aws_lambda.Function:
        lambda_role = self._create_lambda_role(role_name='TenantListRole', table=table, write_permission=False)
        func = aws_lambda.Function(
            self,
            f'{id_}ListTenant',
            function_name=f'{id_}ListTenant',
            runtime=aws_lambda.Runtime.PYTHON_3_7,
            code=aws_lambda.Code.from_asset('.build/service'),
            handler='crud_api.functions.handler.list_tenants',
            role=lambda_role,
            environment={
                'TENANT_MNGT_USER_POOL_ARN': self.user_pool_arn,
                'PROFILE': self._profile,
                'USER_NAME': self._username,
                'TENANTS_TABLE_NAME': table.table_name,
            },
            timeout=core.Duration.seconds(10),
            memory_size=192,
        )
        # Bind GET /tenants to the lambda
        method = self.tenants_resource.add_method(
            http_method="GET",
            integration=aws_apigateway.LambdaIntegration(handler=func),  # GET /tenants
            authorization_type=aws_apigateway.AuthorizationType.COGNITO,
        )
        method_resource: aws_apigateway.Resource = method.node.find_child("Resource")
        method_resource.add_property_override("AuthorizerId", {"Ref": self.api_authorizer.logical_id})
        return func

    def _add_get_lambda_integration(self, id_: str, table: aws_dynamodb.Table) -> aws_lambda.Function:
        lambda_role = self._create_lambda_role(role_name='TenanGetRole', table=table, write_permission=False)
        func = aws_lambda.Function(
            self,
            f'{id_}GetTenant',
            function_name=f'{id_}GetTenant',
            runtime=aws_lambda.Runtime.PYTHON_3_7,
            code=aws_lambda.Code.from_asset('.build/service'),
            handler='crud_api.functions.handler.get_tenant',
            role=lambda_role,
            environment={
                'TENANT_MNGT_USER_POOL_ARN': self.user_pool_arn,
                'PROFILE': self._profile,
                'USER_NAME': self._username,
                'TENANTS_TABLE_NAME': table.table_name,
            },
            timeout=core.Duration.seconds(10),
            memory_size=192,
        )

        # Bind /tenants/{tenant_id} to the lambda
        method = self.tenant_id_resource.add_method(
            http_method="GET",
            integration=aws_apigateway.LambdaIntegration(handler=func),  # GET /tenants/{tenant_id},
            authorization_type=aws_apigateway.AuthorizationType.COGNITO,
        )
        method_resource: aws_apigateway.Resource = method.node.find_child("Resource")
        method_resource.add_property_override("AuthorizerId", {"Ref": self.api_authorizer.logical_id})
        return func

    # read permission is assumed to be mandatory
    def _create_lambda_role(self, role_name: str, table: aws_dynamodb.Table, write_permission: bool) -> aws_iam.Role:
        role = aws_iam.Role(
            self,
            f'{role_name}',
            assumed_by=aws_iam.ServicePrincipal("lambda.amazonaws.com"),
            inline_policies={
                "RegionValidationPolicy":
                    aws_iam.PolicyDocument(statements=[
                        aws_iam.PolicyStatement(actions=["ec2:DescribeRegions"], resources=["*"], effect=aws_iam.Effect.ALLOW),
                    ]),
                "TracingPolicy":
                    aws_iam.PolicyDocument(statements=[
                        aws_iam.PolicyStatement(
                            actions=["ssm:Describe*", "ssm:Get*", "ssm:List*"],
                            resources=["arn:aws:ssm:*"],
                            effect=aws_iam.Effect.ALLOW,
                        ),
                    ])
            },
            # add CloudWatch logging policy
            managed_policies=[aws_iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")],
        )
        # set DynamoDB permissions
        if write_permission:
            table.grant_read_write_data(role)
        else:
            table.grant_read_data(role)
        return role
