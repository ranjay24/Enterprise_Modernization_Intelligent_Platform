import os
from aws_cdk import (
    Stack,
    RemovalPolicy,
    Duration,
    aws_s3 as s3,
    aws_dynamodb as dynamodb,
    aws_ecs as ecs,
    aws_ec2 as ec2,
    aws_elasticloadbalancingv2 as elbv2,
    aws_lambda as _lambda,
    aws_sqs as sqs,
    aws_iam as iam,
    aws_cloudwatch as cloudwatch,
    aws_apigateway as apigw,
    aws_logs as logs,
)
from constructs import Construct


class EMIPBackendStack(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        self.artifacts_bucket = s3.Bucket(
            self,
            "ArtifactsBucket",
            bucket_name=f"emip-artifacts-{self.account}",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            versioned=True,
            encryption=s3.BucketEncryption.S3_MANAGED,
            cors=[
                s3.CorsRule(
                    allowed_methods=[s3.HttpMethods.PUT, s3.HttpMethods.POST, s3.HttpMethods.GET],
                    allowed_origins=["http://localhost:5173", "http://localhost:3000"],
                    allowed_headers=["*"],
                )
            ],
        )

        self.jobs_table = dynamodb.Table(
            self,
            "JobsTable",
            table_name="emip-jobs",
            partition_key=dynamodb.Attribute(
                name="job_id", type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
            point_in_time_recovery=True,
        )

        self.analysis_table = dynamodb.Table(
            self,
            "AnalysisTable",
            table_name="emip-analysis",
            partition_key=dynamodb.Attribute(
                name="job_id", type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="analysis_type", type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
        )

        self.vpc = ec2.Vpc(
            self,
            "EMIPVpc",
            max_azs=2,
            nat_gateways=1,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="Public",
                    subnet_type=ec2.SubnetType.PUBLIC,
                    cidr_mask=24,
                ),
                ec2.SubnetConfiguration(
                    name="Private",
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                    cidr_mask=24,
                ),
            ],
        )

        self.cluster = ecs.Cluster(
            self,
            "EMIPCluster",
            vpc=self.vpc,
            container_insights=True,
        )

        self.task_role = iam.Role(
            self,
            "TaskRole",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
        )
        self.artifacts_bucket.grant_read_write(self.task_role)
        self.jobs_table.grant_read_write_data(self.task_role)
        self.analysis_table.grant_read_write_data(self.task_role)

        self.task_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelWithResponseStream",
                    "bedrock:GetFoundationModel",
                    "bedrock:ListFoundationModels",
                ],
                resources=["*"],
            )
        )

        self.execution_role = iam.Role(
            self,
            "ExecutionRole",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AmazonECSTaskExecutionRolePolicy"
                )
            ],
        )

        self.log_group = logs.LogGroup(
            self,
            "EMIPLogGroup",
            log_group_name="/emip/backend",
            retention=logs.RetentionDays.TWO_WEEKS,
            removal_policy=RemovalPolicy.DESTROY,
        )

        self.alb = elbv2.ApplicationLoadBalancer(
            self,
            "EMIPALB",
            vpc=self.vpc,
            internet_facing=True,
        )

        self.api_security_group = ec2.SecurityGroup(
            self,
            "APISecurityGroup",
            vpc=self.vpc,
            description="Allow inbound HTTP to API",
        )
        self.api_security_group.add_ingress_rule(
            ec2.Peer.any_ipv4(), ec2.Port.tcp(80), "Allow HTTP"
        )

        task_def = ecs.FargateTaskDefinition(
            self,
            "BackendTaskDef",
            memory_limit_mib=1024,
            cpu=512,
            task_role=self.task_role,
            execution_role=self.execution_role,
        )

        container = task_def.add_container(
            "BackendContainer",
            image=ecs.ContainerImage.from_asset("../backend"),
            logging=ecs.LogDrivers.aws_logs(
                stream_prefix="backend",
                log_group=self.log_group,
            ),
            environment={
                "S3_BUCKET": self.artifacts_bucket.bucket_name,
                "DYNAMODB_TABLE": self.jobs_table.table_name,
                "AWS_REGION": self.region,
                "BEDROCK_MODEL_PRIMARY": "amazon.nova-pro-v1:0",
                "BEDROCK_MODEL_FALLBACK": "amazon.nova-lite-v1:0",
                "BEDROCK_MODEL_CODEGEN": "amazon.nova-pro-v1:0",
            },
            port_mappings=[ecs.PortMapping(container_port=8000)],
            health_check=ecs.HealthCheck(
                command=["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"],
                interval=Duration.seconds(30),
                timeout=Duration.seconds(5),
                retries=3,
                start_period=Duration.seconds(60),
            ),
        )

        self.backend_service = ecs.FargateService(
            self,
            "BackendService",
            cluster=self.cluster,
            task_definition=task_def,
            desired_count=1,
            security_groups=[self.api_security_group],
            assign_public_ip=False,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
            ),
        )

        self.backend_service.connections.allow_from(
            self.alb, ec2.Port.tcp(8000), "Allow from ALB"
        )

        self.listener = self.alb.add_listener("Listener", port=80)
        self.listener.add_targets(
            "BackendTarget",
            port=8000,
            targets=[self.backend_service],
            health_check=elbv2.HealthCheck(
                path="/health",
                interval=Duration.seconds(30),
                timeout=Duration.seconds(5),
                healthy_threshold_count=2,
                unhealthy_threshold_count=3,
            ),
        )

        alb_dns = self.alb.load_balancer_dns_name

        self.api = apigw.RestApi(
            self,
            "EMIPAPI",
            rest_api_name="EMIP API",
            description="Enterprise Modernization Intelligence Platform API",
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=apigw.Cors.ALL_ORIGINS,
                allow_methods=apigw.Cors.ALL_METHODS,
                allow_headers=["*"],
            ),
            binary_media_types=["*/*"],
        )

        proxy_resource = self.api.root.add_resource("{proxy+}")
        proxy_resource.add_method(
            "ANY",
            apigw.HttpIntegration(
                f"http://{alb_dns}/{{proxy}}",
                http_method="ANY",
                options=apigw.IntegrationOptions(
                    connection_type=apigw.ConnectionType.INTERNET,
                    request_parameters={
                        "integration.request.path.proxy": "method.request.path.proxy"
                    },
                ),
            ),
            request_parameters={
                "method.request.path.proxy": True,
            },
        )

        self.api.root.add_method(
            "ANY",
            apigw.HttpIntegration(
                f"http://{alb_dns}",
                http_method="GET",
                options=apigw.IntegrationOptions(
                    connection_type=apigw.ConnectionType.INTERNET,
                ),
            ),
        )

        self.queue = sqs.Queue(
            self,
            "AnalysisQueue",
            queue_name="emip-analysis-queue",
            visibility_timeout=Duration.minutes(15),
            retention_period=Duration.days(1),
        )
