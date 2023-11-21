from aws_cdk import (
     Duration,
    Stack,
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_elasticloadbalancingv2 as elbv2,
    aws_autoscaling as autoscaling,
    aws_cloudwatch as cloudwatch,
    aws_sns as sns,
    aws_sns_subscriptions as sns_subs,
    aws_cloudwatch_actions as cloudwatch_actions,
    CfnOutput

)
from constructs import Construct

class WebserverStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        env = self.node.try_get_context('env')
        context = self.node.try_get_context(env)
        region = context["region"]
        vpc_id = context["vpc_id"]
        subnet_1 = context["subnet_id"][0]
        subnet_2 = context["subnet_id"][1]

        amzn_linux = ec2.AmazonLinuxImage(
            generation=ec2.AmazonLinuxGeneration.AMAZON_LINUX,
            edition=ec2.AmazonLinuxEdition.STANDARD,
            virtualization=ec2.AmazonLinuxVirt.HVM,
            storage=ec2.AmazonLinuxStorage.GENERAL_PURPOSE
            )
        
        
        #Import default vpc
        vpc = ec2.Vpc.from_lookup(self, "imported-vpc",
            vpc_id=vpc_id
            )
        
        #Create an SNS topic
        alarm_topic = sns.Topic(self, "newtopic",
           display_name= "Web server notification group" )
        
        #Subscribe to sns topic 
        alarm_topic.add_subscription(sns_subs.EmailSubscription("adachukwuemeka23@gmail.com"))

        #Create load balancer
        lb = elbv2.ApplicationLoadBalancer(self, "AppLb",
            vpc=vpc,
            internet_facing=True,
            load_balancer_name="WebservreAppLoadBalancer")
        
        #Allow ALB to receive internet traffic 
        lb.connections.allow_from_any_ipv4(
            ec2.Port.tcp(80),
            description="Allow Internet access on port 80"
        )
        #Add listenr to ALB 
        lblistener = lb.add_listener("listener",
            port=80,
            )
        
        #Create webserver role
        serverRole = iam.Role(self, "WSRole",
            role_name="WebServerRole",
            assumed_by=iam.ServicePrincipal("ec2.amazonaws.com")
            )
        #Add managed policy to server role
        serverRole.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSSMManagedInstancecore"))
        serverRole.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name("AmazonS3ReadOnlyAccess"))

        #Read bootstrap scripts
        with open("bootstrap/httpd.sh", mode="r") as file:
            userdata = file.read()

        #Create autoscaling group with ec2 instances
        WebseverASG= autoscaling.AutoScalingGroup(self, "serverSG",
            vpc=vpc,
            instance_type=ec2.InstanceType(instance_type_identifier="t2.micro"),
            machine_image=amzn_linux,
            role=serverRole,
            user_data=ec2.UserData.custom(userdata),
            min_capacity=4,
            max_capacity=5)
        
        #Allow WebserverASG to receive traffic from the ALB( listener rule)
        WebseverASG.connections.allow_from(lb, ec2.Port.tcp(80),
            description="Allow WebserverASG to receive traffic from the ALB ")

        #Make WebserverASG the target for the Application Load Balancer(Target group)
        lblistener.add_targets("listenerID",
            port=80,
            targets=[WebseverASG],
            target_group_name="webserverTG")

        #Creating a cloudwatch alarm for my auto scaling group 
        #EC2 metric for CPU
        webserver_metric = cloudwatch.Metric(
            namespace="AWS/ApplicationELB",
            metric_name="UnHealthyHostCount"
        )

        #Alarm for auto scaling group 
        webserver_alarm = cloudwatch.Alarm(self, "webserveralarm",
            alarm_description="Number of unhealthy threashhold",
            alarm_name="WebServerAlarm",
            metric=webserver_metric,
            actions_enabled=True,
            threshold=2,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            evaluation_periods=2,
            datapoints_to_alarm=1,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING
            )
      
        #nform Sns state on Alarm state
        webserver_alarm.add_alarm_action(cloudwatch_actions.SnsAction(webserver_alarm))


        #Output of the ALB domain 
        output_1 = CfnOutput(self, "linkURL",
            value=f"http://{lb.load_balancer_dns_name}",
            description="Web server Domain url")
