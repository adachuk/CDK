from aws_cdk import (
     aws_s3 as s3,
     Stack,
     Tags
)

from constructs import Construct

class CdkprojectStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # The code that defines your stack goes here

        bukcet = s3.Bucket(
            self,
            "CdkprojectBucket",
            bucket_name="lucysbucket01h2",
            versioned=True,
            encryption=s3.BucketEncryption.KMS
            )
        bucket_tag = Tags.of(bukcet).add(key="ada",value="bukcet")
