from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_ecr as ecr,
    aws_iam as iam,
    aws_elasticloadbalancingv2 as elbv2,
    aws_route53 as route53,
    aws_ecr_assets as assets,
    aws_ecs_patterns as ecs_patterns,
    aws_route53_targets as target,
    CfnOutput,
    Aws,
    Duration,
    Fn

)
from constructs import Construct
import os

class MigrationStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        env = self.node.try_get_context('env')
        context = self.node.try_get_context(env)
        region = context["region"]
        vpc_id = context["vpc_id"]
        subnet_1 = context["subnet_id"][0]
        subnet_2 = context["subnet_id"][1]
        ecr_repo_assets = context["ecr_repo_assets"]
        
        vpc= ec2.Vpc.from_lookup(self, "defaultVpc",
            vpc_id=vpc_id,
         )
        
        
        #Create a VPC endpoint(Allows AWS resources communicate with eachother securely over the network without IGW,NAT or VPN)
        VpcEndpoint = ec2.InterfaceVpcEndpoint(self, "Vpc Enpoint",
            vpc=vpc,
            service=ec2.InterfaceVpcEndpointService(
                name="com.amazonaws.us-east-1.ecr.api",
                port=443),
                subnets=ec2.SubnetSelection(
                    availability_zones=["us-east-1a", "us-east-1b","us-east-1c", "us-east-1d","us-east-1e", "us-east-1f"],    
                ))
            
        # creating a subnet object
        subnet_a = ec2.Subnet.from_subnet_id(self, "impotedSubnet",
            subnet_id=subnet_1)                                      

        # creating a subnet object
        subnet_b = ec2.Subnet.from_subnet_id(self, "newSubnet",
            subnet_id=subnet_2)    
        
        # Alb security group that is open to port 80
        sg_alb = ec2.SecurityGroup(self,
            "alb-sg",
            vpc=vpc,
            allow_all_outbound=True,
           )
        
        sg_alb.add_ingress_rule(
            peer=ec2.Peer.any_ipv4(),
            connection=ec2.Port.tcp(80),
            description="allow all connections from port 80"
        )
        #ecs SG that allows traffic from alb security group 
        sg_ecs = ec2.SecurityGroup(self,
            "ecs-sg",
            vpc=vpc,
            allow_all_outbound=True,
           )
        
        #Inboud rule for ecs security group 
        sg_ecs.add_ingress_rule(
            peer=ec2.Peer.security_group_id(security_group_id=sg_alb.security_group_id),
            connection=ec2.Port.tcp(80),
            description="allow connection from alb security group"
        )
        
        #Create ECS task execution role 
        task_execution_Role = iam.Role(self, "TaskdefRole",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
            description="Role for ecs to make API calls on my behalf, e.g pull images from ECR",
            role_name="ECS-task-execution-Role")

        #Grant all access to the task execution role 
        task_execution_Role.add_to_policy(iam.PolicyStatement(actions=["*"],
            resources=["*"]))

        #Create a Fargate task definition for webserver
        fargate_task_def = ecs.FargateTaskDefinition(self, "TaskDef",
            execution_role=task_execution_Role,
            cpu=256,
            memory_limit_mib=1024)
        
        #Get the docker file directory 
        path = os.getcwd()
        image_asset = assets.DockerImageAsset(self, "image-asset",
            directory=os.path.join(path, "Docker")
        )

        
        #Define repo
        ecr_repo = ecr.Repository.from_repository_name(self,"webapp-ecr",
            repository_name=f"{ecr_repo_assets}-{Aws.ACCOUNT_ID}-{region}")

        #  image based on the ecr repo
        webapp_image = ecs.EcrImage.from_ecr_repository(
            repository=ecr_repo,
            tag=image_asset.asset_hash
        )

        #Add container to fargate task
        webapp_container = fargate_task_def.add_container(
            "webappContainer",
            container_name="webappcontainer",
            image=webapp_image,
            port_mappings=[ecs.PortMapping(container_port=80)],
            cpu=256,
            memory_limit_mib=1024)
        
        #Create port mappings for the container
        webapp_container.add_port_mappings(ecs.PortMapping(container_port=80, protocol=ecs.Protocol.TCP))

        #define a web app cluster name
        webapp_cluster = ecs.Cluster(self, "Cluster",
            vpc = vpc,
            cluster_name="webapp-Cluster")
        
        #create a web app ecs cluster
        webapp_service = ecs.FargateService(self, "ecscluster",
            task_definition=fargate_task_def,
            cluster=webapp_cluster,
            assign_public_ip=True,
            security_groups=[sg_ecs],
            vpc_subnets=ec2.SubnetSelection(subnets=[subnet_a, subnet_b]),
            desired_count=2,
            service_name="web-app-fargateService")
        
        #Create an application load balancer to distribute http traffic accross targets(ECS)
        ecs_alb = elbv2.ApplicationLoadBalancer(self, "ecs-ALB",
            vpc=vpc,
            http2_enabled=True,
            internet_facing=True,
            security_group=sg_alb,
            load_balancer_name="web-app-load-balancer")

        #create target group 
        web_app_targetgroup = elbv2.ApplicationTargetGroup(self,"targetgroup",
            port=80,
            vpc=vpc,
            targets=[webapp_service],
            protocol=elbv2.ApplicationProtocol.HTTP,
            target_type=elbv2.TargetType.IP,
            health_check=elbv2.HealthCheck(enabled=True,
            healthy_http_codes="200",
            healthy_threshold_count=5,
            interval=Duration.seconds(20),
            path="/",
            port="80",
            protocol=elbv2.Protocol.HTTP,
            unhealthy_threshold_count=5))
        
        
        #create listeners and routing 
        listener = ecs_alb.add_listener("Listerner", 
            port=80,
            default_target_groups=[web_app_targetgroup]
            )
        
        #Route 53 hosted zone 
        hosted_zone = route53.PrivateHostedZone(self, "HostedZone",
            zone_name="lucychatapp.local",
            vpc=vpc
         )
        
        #Creates an A record for Route 53 dns
        route53.ARecord(self, "ARecord",
            zone= hosted_zone,
            record_name=hosted_zone.zone_name,
            target=route53.RecordTarget.from_alias(target.LoadBalancerTarget(ecs_alb))
         )