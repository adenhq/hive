"""
AWS S3 tool credentials.

Contains credentials for AWS S3 cloud storage integration.
"""

from .base import CredentialSpec

S3_CREDENTIALS = {
    "aws_s3": CredentialSpec(
        env_var="AWS_ACCESS_KEY_ID",
        tools=[
            "s3_upload",
            "s3_download",
            "s3_list",
            "s3_delete",
            "s3_check_credentials",
        ],
        required=True,
        startup_required=False,
        help_url="https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_access-keys.html",
        description="AWS access key for S3 operations",
        # Auth method support
        aden_supported=False,
        direct_api_key_supported=True,
        api_key_instructions="""To get AWS credentials for S3:
1. Go to AWS IAM Console > Users
2. Select your user (or create one)
3. Go to "Security credentials" tab
4. Click "Create access key"
5. Copy the Access Key ID and Secret Access Key
6. Set environment variables:
   export AWS_ACCESS_KEY_ID=your_access_key
   export AWS_SECRET_ACCESS_KEY=your_secret_key
   export AWS_DEFAULT_REGION=us-east-1""",
        # Credential store mapping
        credential_id="aws_s3",
        credential_key="access_key_id",
    ),
}
