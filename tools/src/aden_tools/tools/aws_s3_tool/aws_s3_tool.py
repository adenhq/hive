"""
AWS S3 Tool - Object storage operations via AWS S3.

Supports:
- AWS access key authentication (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_DEFAULT_REGION)

Use Cases:
- List available S3 buckets in an AWS account
- List objects (files) within a specific bucket path
- Read text-based S3 objects (JSON, CSV, logs) into agent context

API Reference: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3.html
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError
from fastmcp import FastMCP

if TYPE_CHECKING:
    from aden_tools.credentials import CredentialStoreAdapter

MAX_OBJECT_SIZE_BYTES = 2 * 1024 * 1024


class _S3Client:
    """Internal client wrapping AWS S3 API calls via boto3."""

    def __init__(self, access_key_id: str, secret_access_key: str, region: str = "us-east-1"):
        self._client = boto3.client(
            "s3",
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            region_name=region,
        )

    def _s3(self):
        return self._client

    def list_buckets(self) -> dict[str, Any]:
        """List all S3 buckets in the AWS account."""
        response = self._s3().list_buckets()
        buckets = []
        for bucket in response.get("Buckets", []):
            buckets.append(
                {
                    "name": bucket["Name"],
                    "creation_date": bucket["CreationDate"].isoformat()
                    if bucket.get("CreationDate")
                    else None,
                }
            )
        return {"buckets": buckets, "count": len(buckets)}

    def list_objects(
        self,
        bucket_name: str,
        prefix: str = "",
        max_keys: int = 1000,
    ) -> dict[str, Any]:
        """List objects in an S3 bucket with optional prefix filter."""
        params: dict[str, Any] = {"Bucket": bucket_name, "MaxKeys": min(max_keys, 1000)}
        if prefix:
            params["Prefix"] = prefix

        response = self._s3().list_objects_v2(**params)

        objects = []
        for obj in response.get("Contents", []):
            objects.append(
                {
                    "key": obj["Key"],
                    "size": obj["Size"],
                    "last_modified": obj["LastModified"].isoformat()
                    if obj.get("LastModified")
                    else None,
                    "etag": obj.get("ETag", "").strip('"'),
                    "storage_class": obj.get("StorageClass", "STANDARD"),
                }
            )

        return {
            "bucket": bucket_name,
            "prefix": prefix,
            "objects": objects,
            "count": len(objects),
            "is_truncated": response.get("IsTruncated", False),
            "next_continuation_token": response.get("NextContinuationToken"),
        }

    def get_object_content(
        self,
        bucket_name: str,
        object_key: str,
        max_size_bytes: int = MAX_OBJECT_SIZE_BYTES,
    ) -> dict[str, Any]:
        """Get the content of an S3 object with size limit protection."""
        s3_client = self._s3()

        head_response = s3_client.head_object(Bucket=bucket_name, Key=object_key)
        object_size = head_response.get("ContentLength", 0)

        if object_size > max_size_bytes:
            return {
                "error": f"Object too large ({object_size} bytes). Maximum allowed: {max_size_bytes} bytes.",
                "object_key": object_key,
                "bucket": bucket_name,
                "size_bytes": object_size,
                "max_allowed_bytes": max_size_bytes,
            }

        response = s3_client.get_object(Bucket=bucket_name, Key=object_key)
        content_bytes = response["Body"].read()

        try:
            content = content_bytes.decode("utf-8")
        except UnicodeDecodeError:
            try:
                content = content_bytes.decode("latin-1")
            except Exception:
                return {
                    "error": "Unable to decode object content. File may be binary.",
                    "object_key": object_key,
                    "bucket": bucket_name,
                    "size_bytes": object_size,
                    "content_type": response.get("ContentType", "unknown"),
                }

        return {
            "bucket": bucket_name,
            "object_key": object_key,
            "content": content,
            "size_bytes": object_size,
            "content_type": response.get("ContentType", "application/octet-stream"),
            "last_modified": response.get("LastModified").isoformat()
            if response.get("LastModified")
            else None,
            "etag": response.get("ETag", "").strip('"'),
        }


def register_tools(
    mcp: FastMCP,
    credentials: CredentialStoreAdapter | None = None,
) -> None:
    """Register AWS S3 tools with the MCP server."""

    def _get_aws_credentials() -> dict[str, str] | dict[str, Any]:
        """Get AWS credentials from credential manager or environment."""
        access_key_id = None
        secret_access_key = None
        region = None

        if credentials is not None:
            access_key_id = credentials.get("aws_s3")
            secret_access_key = credentials.get("aws_s3_secret")
            region = credentials.get("aws_s3_region")
        else:
            access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
            secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
            region = os.getenv("AWS_DEFAULT_REGION")

        if not access_key_id or not secret_access_key:
            return {
                "error": "AWS S3 credentials not configured",
                "help": (
                    "Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables. "
                    "Optionally set AWS_DEFAULT_REGION (defaults to us-east-1). "
                    "Get your credentials at https://console.aws.amazon.com/iam"
                ),
            }

        return {
            "access_key_id": access_key_id,
            "secret_access_key": secret_access_key,
            "region": region or "us-east-1",
        }

    def _get_client() -> _S3Client | dict[str, Any]:
        """Get an S3 client, or return an error dict if no credentials."""
        creds = _get_aws_credentials()
        if isinstance(creds, dict) and "error" in creds:
            return creds
        return _S3Client(
            access_key_id=creds["access_key_id"],
            secret_access_key=creds["secret_access_key"],
            region=creds["region"],
        )

    def _s3_error(e: Exception) -> dict[str, Any]:
        """Format AWS/Boto3 errors into consistent dict format."""
        if isinstance(e, ClientError):
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_msg = e.response.get("Error", {}).get("Message", str(e))
            return {"error": f"AWS Error [{error_code}]: {error_msg}"}
        elif isinstance(e, NoCredentialsError):
            return {
                "error": "AWS credentials not found. Please configure AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY"
            }
        elif isinstance(e, BotoCoreError):
            return {"error": f"AWS SDK Error: {str(e)}"}
        return {"error": str(e)}

    @mcp.tool()
    def list_s3_buckets() -> dict:
        """
        List all S3 buckets available in the current AWS account.

        Returns:
            Dict with list of buckets (name, creation_date) and count.

        Example:
            list_s3_buckets()
            # Returns: {"buckets": [{"name": "my-bucket", "creation_date": "2024-01-15T10:30:00"}], "count": 1}
        """
        client = _get_client()
        if isinstance(client, dict):
            return client
        try:
            return client.list_buckets()
        except (ClientError, BotoCoreError, NoCredentialsError) as e:
            return _s3_error(e)

    @mcp.tool()
    def list_s3_objects(
        bucket_name: str,
        prefix: str = "",
        max_keys: int = 1000,
    ) -> dict:
        """
        List objects (files) within an S3 bucket.

        Args:
            bucket_name: Name of the S3 bucket to list objects from
            prefix: Optional prefix to filter objects (e.g., "logs/2024/")
            max_keys: Maximum number of objects to return (1-1000, default 1000)

        Returns:
            Dict with list of objects (key, size, last_modified, etag, storage_class)
            and pagination info.

        Example:
            list_s3_objects(bucket_name="my-bucket", prefix="data/", max_keys=100)
            # Returns: {"bucket": "my-bucket", "objects": [...], "count": 50}
        """
        client = _get_client()
        if isinstance(client, dict):
            return client

        if not bucket_name:
            return {"error": "bucket_name is required"}

        if max_keys < 1:
            return {"error": "max_keys must be at least 1"}

        try:
            return client.list_objects(bucket_name, prefix, max_keys)
        except (ClientError, BotoCoreError, NoCredentialsError) as e:
            return _s3_error(e)

    @mcp.tool()
    def get_s3_object_content(
        bucket_name: str,
        object_key: str,
    ) -> dict:
        """
        Read the content of a text-based S3 object (JSON, CSV, logs, etc.).

        Args:
            bucket_name: Name of the S3 bucket containing the object
            object_key: Key (path) of the object to read (e.g., "data/sales.csv")

        Returns:
            Dict with object content, metadata (size, content_type, last_modified).
            Returns error if object exceeds 2MB size limit.

        Example:
            get_s3_object_content(bucket_name="my-bucket", object_key="config.json")
            # Returns: {"content": '{"setting": true}', "size_bytes": 18, "content_type": "application/json"}
        """
        client = _get_client()
        if isinstance(client, dict):
            return client

        if not bucket_name:
            return {"error": "bucket_name is required"}

        if not object_key:
            return {"error": "object_key is required"}

        try:
            return client.get_object_content(bucket_name, object_key)
        except (ClientError, BotoCoreError, NoCredentialsError) as e:
            return _s3_error(e)
