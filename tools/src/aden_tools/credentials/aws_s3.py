"""
AWS S3 tool credentials.

Contains credentials for AWS S3 Object Storage access.
"""

from .base import CredentialSpec

AWS_S3_CREDENTIALS = {
    "aws_s3": CredentialSpec(
        env_var="AWS_ACCESS_KEY_ID",
        tools=[
            "list_s3_buckets",
            "list_s3_objects",
            "get_s3_object_content",
        ],
        required=True,
        startup_required=False,
        help_url="https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_access-keys.html",
        description="AWS Access Key ID for S3 object storage access",
        aden_supported=False,
        direct_api_key_supported=True,
        api_key_instructions="""To set up AWS S3 authentication:

1. Log in to AWS Console at https://console.aws.amazon.com
2. Navigate to IAM > Users > Create user (or select existing)
3. Add permissions: "AmazonS3ReadOnlyAccess" (for read-only) or "AmazonS3FullAccess"
4. Create access keys: Security credentials > Create access key
5. Copy the Access Key ID and Secret Access Key

Set environment variables:
  export AWS_ACCESS_KEY_ID=your_access_key_id
  export AWS_SECRET_ACCESS_KEY=your_secret_access_key
  export AWS_DEFAULT_REGION=us-east-1 (or your preferred region)""",
        health_check_endpoint="https://s3.amazonaws.com",
        health_check_method="GET",
        credential_id="aws_s3",
        credential_key="access_key_id",
    ),
    "aws_s3_secret": CredentialSpec(
        env_var="AWS_SECRET_ACCESS_KEY",
        tools=[
            "list_s3_buckets",
            "list_s3_objects",
            "get_s3_object_content",
        ],
        required=True,
        startup_required=False,
        help_url="https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_access-keys.html",
        description="AWS Secret Access Key for S3 object storage access",
        aden_supported=False,
        direct_api_key_supported=True,
        api_key_instructions="Set AWS_SECRET_ACCESS_KEY environment variable to your AWS secret key",
        credential_id="aws_s3",
        credential_key="secret_access_key",
    ),
    "aws_s3_region": CredentialSpec(
        env_var="AWS_DEFAULT_REGION",
        tools=[
            "list_s3_buckets",
            "list_s3_objects",
            "get_s3_object_content",
        ],
        required=False,
        startup_required=False,
        help_url="https://docs.aws.amazon.com/general/latest/gr/rande.html#regional-endpoints",
        description="AWS Region for S3 operations (defaults to us-east-1)",
        aden_supported=False,
        direct_api_key_supported=True,
        api_key_instructions="Set AWS_DEFAULT_REGION environment variable (e.g., us-east-1, eu-west-1)",
        credential_id="aws_s3",
        credential_key="region",
    ),
}
