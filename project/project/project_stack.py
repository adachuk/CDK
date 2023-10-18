from aws_cdk import (
    Stack,
     aws_ec2 as ec2,
     aws_ecs as ecs,
     aws_ecr as ecr,
     aws_ecs_patterns as ecs_patterns,
     CfnOutput as output,
     aws_iam as iam,
     aws_route53 as route53,
     aws_route53_targets as target,
     aws_elasticloadbalancingv2 as elbv2,
     Duration
     
     )
from constructs import Construct

class ProjectStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # context base  environment variables 
        env = self.node.try_get_context('env')
        context = self.node.try_get_context(env)
        vpc_id = context["vpc_id"]
        subnet_1 = context["subnet_id"][0]
        subnet_2 = context["subnet_id"][1]
        
        # import default vpc
        vpc = ec2.Vpc.from_lookup(self, "imported-vpc",
            vpc_id=vpc_id
            )

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
        
        
        # ECStask execution role
        ecs_ex_iam_role =  iam.Role(
            self, "Role",
            assumed_by= iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
            role_name="ecs-execution-role"
        )
        
        # Fargate task definition
        chat_app_task_serv_def = ecs.FargateTaskDefinition(self, "task-definition",
            task_role=ecs_ex_iam_role, 
            cpu=256,
            memory_limit_mib=1024                             
         )
        

        # temp granting all access to the ecs execution role 
        ecs_ex_iam_role.add_to_policy(iam.PolicyStatement(actions=["*"],
            resources=["*"]
        
        ))

         #here i import the ECR repo i created manaully on aws 
        ecr_repo = ecr.Repository.from_repository_name(self,"chatapp-ecr",
                 repository_name="mychatapp") 
    

        # here is my image based on the chatapp ecr repo
        chatapp_image = ecs.EcrImage.from_ecr_repository(
            repository=ecr_repo,
            tag="latest"
        )

        # create ecr repo 
        #chatapp_repo = ecr.Repository(self, "chat-app-repo")

        # here i add a container 
        chat_app_container = chat_app_task_serv_def.add_container(
            "chatappContainer",
            image=chatapp_image,
            port_mappings=[ecs.PortMapping(container_port=3000)],
            cpu=256,
            memory_limit_mib=1024,
            
            )
        
        chat_app_cluster = ecs.Cluster(self, "ecsCluster",
             vpc=vpc,
            cluster_name="chat-app-cluster"
            )

        # create fargate cluster
        chat_app_service = ecs.FargateService(
            self, "chatappCluster",
            task_definition=chat_app_task_serv_def,
            cluster=chat_app_cluster,
            desired_count=1,
            security_groups=[sg_ecs],
            vpc_subnets=ec2.SubnetSelection(subnets=[subnet_a, subnet_b]),
            assign_public_ip=True
        )   
            #Create an application load balancer
        lb = elbv2.ApplicationLoadBalancer(self, "loadbalancer",
            vpc=vpc,
            internet_facing=True,
            vpc_subnets=ec2.SubnetSelection(subnets=[subnet_a, subnet_b]),
            load_balancer_name="chat-app-alb"
            )

        # create an application load balancer target group 
        tg = elbv2.ApplicationTargetGroup(self,"tg1",
            port=80,
            vpc=vpc,
            protocol=elbv2.Protocol.HTTP,
            target_type=elbv2.TargetType.IP,
            target_group_name="we-did-it-finally",
            targets=[chat_app_service],
            health_check=elbv2.HealthCheck(enabled=True,
            healthy_http_codes="200",
            healthy_threshold_count=5,
            interval=Duration.seconds(20),
            path="/",
            port="3000",
            protocol=elbv2.Protocol.HTTP,
            unhealthy_threshold_count=5


            )                               
            )
        
        # Listener port for ALB
        listner = lb.add_listener("listner",
             port=80,
             protocol=elbv2.Protocol.HTTP,
             default_target_groups=[tg]
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
            target=route53.RecordTarget.from_alias(target.LoadBalancerTarget(lb))
         )