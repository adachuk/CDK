from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
    Tags,
    CfnOutput,
    
)
from constructs import Construct

class VpcStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        #Creating a custom VPC with 

        vpc = ec2.Vpc(self, "customVPC",
            vpc_name="CustomVpc",
            nat_gateways=0,
            cidr="10.0.0.0/16",
            enable_dns_hostnames=True,
            enable_dns_support=True,
            max_azs=2,
            subnet_configuration=[ec2.SubnetConfiguration(
                subnet_type=ec2.SubnetType.PUBLIC,
                name="Public1",
                cidr_mask=24),
                ec2.SubnetConfiguration(
                subnet_type=ec2.SubnetType.PRIVATE_ISOLATED,
                name="Private1",
                cidr_mask=24),
                ]
        )
        Tags.of(vpc).add(key="name",value="customvpc")

        CfnOutput(self, "customVpc",
            value=vpc.vpc_id,
            export_name="customVpc")