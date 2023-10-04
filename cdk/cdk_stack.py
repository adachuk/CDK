from aws_cdk import (
     aws_s3 as s3,
     Stack,
     CfnOutput as output
     
)
from constructs import Construct

class CdkStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # The code that defines your stack goes here
        
        mybucket = s3.Bucket(
            self,
            "NewBucket",
            bucket_name="adalucysbucket",
            versioned=False,
            encryption=s3.BucketEncryption.KMS,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL
            
            
        )
        bucket_name  = output(
            self, 
            "Newbucket", 
            value=mybucket.bucket_name,
            description=f"my first cdk bucket",
            export_name="bucketoutput",
        )
        print(mybucket.bucket_name)