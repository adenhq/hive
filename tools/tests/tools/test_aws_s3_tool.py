"""
Tests for AWS S3 Object Storage tool.

Covers:
- _S3Client methods (list_buckets, list_objects, get_object_content)
- Error handling (ClientError, NoCredentialsError, BotoCoreError)
- Credential retrieval (CredentialStoreAdapter vs env var)
- All 3 MCP tool functions
- Input validation
- Size limit protection for get_object_content
"""

from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError

from aden_tools.tools.aws_s3_tool.aws_s3_tool import (
    MAX_OBJECT_SIZE_BYTES,
    _S3Client,
    register_tools,
)


def _make_datetime(iso_str: str = "2024-01-15T10:30:00+00:00") -> datetime:
    """Parse ISO format string to datetime."""
    return datetime.fromisoformat(iso_str)


class TestS3ClientListBuckets:
    def setup_method(self):
        self.client = _S3Client(
            access_key_id="test_access_key",
            secret_access_key="test_secret_key",
            region="us-east-1",
        )

    def test_list_buckets_success(self):
        mock_s3 = MagicMock()
        mock_s3.list_buckets.return_value = {
            "Buckets": [
                {"Name": "bucket-one", "CreationDate": _make_datetime()},
                {"Name": "bucket-two", "CreationDate": _make_datetime("2024-02-20T14:00:00+00:00")},
            ]
        }

        with patch.object(self.client, "_client", mock_s3):
            result = self.client.list_buckets()

        assert result["count"] == 2
        assert len(result["buckets"]) == 2
        assert result["buckets"][0]["name"] == "bucket-one"
        assert result["buckets"][1]["name"] == "bucket-two"

    def test_list_buckets_empty(self):
        mock_s3 = MagicMock()
        mock_s3.list_buckets.return_value = {"Buckets": []}

        with patch.object(self.client, "_client", mock_s3):
            result = self.client.list_buckets()

        assert result["count"] == 0
        assert result["buckets"] == []


class TestS3ClientListObjects:
    def setup_method(self):
        self.client = _S3Client(
            access_key_id="test_access_key",
            secret_access_key="test_secret_key",
            region="us-east-1",
        )

    def test_list_objects_success(self):
        mock_s3 = MagicMock()
        mock_s3.list_objects_v2.return_value = {
            "Contents": [
                {
                    "Key": "file1.csv",
                    "Size": 1024,
                    "LastModified": _make_datetime(),
                    "ETag": '"abc123"',
                    "StorageClass": "STANDARD",
                },
                {
                    "Key": "folder/file2.json",
                    "Size": 2048,
                    "LastModified": _make_datetime(),
                    "ETag": '"def456"',
                    "StorageClass": "STANDARD",
                },
            ],
            "IsTruncated": False,
        }

        with patch.object(self.client, "_client", mock_s3):
            result = self.client.list_objects("my-bucket", prefix="data/")

        assert result["bucket"] == "my-bucket"
        assert result["prefix"] == "data/"
        assert result["count"] == 2
        assert len(result["objects"]) == 2
        assert result["objects"][0]["key"] == "file1.csv"
        assert result["objects"][0]["size"] == 1024
        assert result["objects"][1]["key"] == "folder/file2.json"

    def test_list_objects_with_prefix(self):
        mock_s3 = MagicMock()
        mock_s3.list_objects_v2.return_value = {
            "Contents": [
                {
                    "Key": "logs/2024/app.log",
                    "Size": 500,
                    "LastModified": _make_datetime(),
                    "ETag": '"xyz"',
                    "StorageClass": "STANDARD",
                },
            ],
            "IsTruncated": False,
        }

        with patch.object(self.client, "_client", mock_s3):
            result = self.client.list_objects("logs-bucket", prefix="logs/2024/")

        mock_s3.list_objects_v2.assert_called_once()
        call_args = mock_s3.list_objects_v2.call_args[1]
        assert call_args["Bucket"] == "logs-bucket"
        assert call_args["Prefix"] == "logs/2024/"
        assert result["prefix"] == "logs/2024/"

    def test_list_objects_empty_bucket(self):
        mock_s3 = MagicMock()
        mock_s3.list_objects_v2.return_value = {"Contents": [], "IsTruncated": False}

        with patch.object(self.client, "_client", mock_s3):
            result = self.client.list_objects("empty-bucket")

        assert result["count"] == 0
        assert result["objects"] == []

    def test_list_objects_truncated(self):
        mock_s3 = MagicMock()
        mock_s3.list_objects_v2.return_value = {
            "Contents": [
                {
                    "Key": "file1.txt",
                    "Size": 100,
                    "LastModified": _make_datetime(),
                    "ETag": '"a"',
                    "StorageClass": "STANDARD",
                },
            ],
            "IsTruncated": True,
            "NextContinuationToken": "token123",
        }

        with patch.object(self.client, "_client", mock_s3):
            result = self.client.list_objects("my-bucket", max_keys=1)

        assert result["is_truncated"] is True
        assert result["next_continuation_token"] == "token123"

    def test_list_objects_max_keys_capped(self):
        mock_s3 = MagicMock()
        mock_s3.list_objects_v2.return_value = {"Contents": [], "IsTruncated": False}

        with patch.object(self.client, "_client", mock_s3):
            self.client.list_objects("my-bucket", max_keys=5000)

        call_args = mock_s3.list_objects_v2.call_args[1]
        assert call_args["MaxKeys"] == 1000


class TestS3ClientGetObjectContent:
    def setup_method(self):
        self.client = _S3Client(
            access_key_id="test_access_key",
            secret_access_key="test_secret_key",
            region="us-east-1",
        )

    def test_get_object_content_success(self):
        content = b'{"name": "test", "value": 42}'
        mock_body = MagicMock()
        mock_body.read.return_value = content

        mock_s3 = MagicMock()
        mock_s3.head_object.return_value = {
            "ContentLength": len(content),
            "ContentType": "application/json",
            "LastModified": _make_datetime(),
            "ETag": '"json123"',
        }
        mock_s3.get_object.return_value = {
            "Body": mock_body,
            "ContentType": "application/json",
            "LastModified": _make_datetime(),
            "ETag": '"json123"',
        }

        with patch.object(self.client, "_client", mock_s3):
            result = self.client.get_object_content("my-bucket", "data/config.json")

        assert result["bucket"] == "my-bucket"
        assert result["object_key"] == "data/config.json"
        assert result["content"] == '{"name": "test", "value": 42}'
        assert result["size_bytes"] == len(content)
        assert result["content_type"] == "application/json"

    def test_get_object_content_csv(self):
        content = b"id,name,value\n1,Alice,100\n2,Bob,200"
        mock_body = MagicMock()
        mock_body.read.return_value = content

        mock_s3 = MagicMock()
        mock_s3.head_object.return_value = {
            "ContentLength": len(content),
            "ContentType": "text/csv",
            "LastModified": _make_datetime(),
            "ETag": '"csv123"',
        }
        mock_s3.get_object.return_value = {
            "Body": mock_body,
            "ContentType": "text/csv",
            "LastModified": _make_datetime(),
            "ETag": '"csv123"',
        }

        with patch.object(self.client, "_client", mock_s3):
            result = self.client.get_object_content("data-bucket", "exports/sales.csv")

        assert "id,name,value" in result["content"]
        assert result["content_type"] == "text/csv"

    def test_get_object_content_too_large(self):
        large_size = MAX_OBJECT_SIZE_BYTES + 1000

        mock_s3 = MagicMock()
        mock_s3.head_object.return_value = {"ContentLength": large_size}

        with patch.object(self.client, "_client", mock_s3):
            result = self.client.get_object_content("my-bucket", "large-file.bin")

        assert "error" in result
        assert "too large" in result["error"].lower()
        assert result["size_bytes"] == large_size
        assert result["max_allowed_bytes"] == MAX_OBJECT_SIZE_BYTES

    def test_get_object_content_binary_fallback_to_latin1(self):
        content = b"Some text with \xe9 accent"
        mock_body = MagicMock()
        mock_body.read.return_value = content

        mock_s3 = MagicMock()
        mock_s3.head_object.return_value = {
            "ContentLength": len(content),
            "ContentType": "text/plain",
        }
        mock_s3.get_object.return_value = {
            "Body": mock_body,
            "ContentType": "text/plain",
            "LastModified": _make_datetime(),
            "ETag": '"txt123"',
        }

        with patch.object(self.client, "_client", mock_s3):
            result = self.client.get_object_content("my-bucket", "notes.txt")

        assert result["content"] == "Some text with é accent"

    def test_get_object_content_truly_binary(self):
        content = bytes(range(256))
        mock_body = MagicMock()
        mock_body.read.return_value = content

        mock_s3 = MagicMock()
        mock_s3.head_object.return_value = {
            "ContentLength": len(content),
            "ContentType": "application/octet-stream",
        }
        mock_s3.get_object.return_value = {
            "Body": mock_body,
            "ContentType": "application/octet-stream",
            "LastModified": _make_datetime(),
            "ETag": '"bin123"',
        }

        with patch.object(self.client, "_client", mock_s3):
            result = self.client.get_object_content("my-bucket", "binary-file.exe")

        assert "error" in result
        assert "binary" in result["error"].lower()


class TestToolRegistration:
    def test_register_tools_registers_all_tools(self):
        mcp = MagicMock()
        mcp.tool.return_value = lambda fn: fn
        register_tools(mcp)
        assert mcp.tool.call_count == 3

    def test_no_credentials_returns_error(self):
        mcp = MagicMock()
        registered_fns = []
        mcp.tool.return_value = lambda fn: registered_fns.append(fn) or fn

        with patch.dict("os.environ", {}, clear=True):
            register_tools(mcp, credentials=None)
            list_fn = next(f for f in registered_fns if f.__name__ == "list_s3_buckets")
            result = list_fn()

        assert "error" in result
        assert "not configured" in result["error"]

    def test_credentials_from_credential_manager(self):
        mcp = MagicMock()
        registered_fns = []
        mcp.tool.return_value = lambda fn: registered_fns.append(fn) or fn

        cred_manager = MagicMock()
        cred_manager.get.side_effect = lambda name: {
            "aws_s3": "test_access_key",
            "aws_s3_secret": "test_secret_key",
            "aws_s3_region": "us-west-2",
        }.get(name)

        register_tools(mcp, credentials=cred_manager)

        fn = next(f for f in registered_fns if f.__name__ == "list_s3_buckets")

        with patch("aden_tools.tools.aws_s3_tool.aws_s3_tool._S3Client") as MockClient:
            instance = MockClient.return_value
            instance.list_buckets.return_value = {"buckets": [], "count": 0}
            fn()

        MockClient.assert_called_once_with(
            access_key_id="test_access_key",
            secret_access_key="test_secret_key",
            region="us-west-2",
        )

    def test_credentials_from_env_vars(self):
        mcp = MagicMock()
        registered_fns = []
        mcp.tool.return_value = lambda fn: registered_fns.append(fn) or fn

        register_tools(mcp, credentials=None)

        fn = next(f for f in registered_fns if f.__name__ == "list_s3_buckets")

        with (
            patch.dict(
                "os.environ",
                {
                    "AWS_ACCESS_KEY_ID": "env_access_key",
                    "AWS_SECRET_ACCESS_KEY": "env_secret_key",
                    "AWS_DEFAULT_REGION": "eu-west-1",
                },
            ),
            patch("aden_tools.tools.aws_s3_tool.aws_s3_tool._S3Client") as MockClient,
        ):
            instance = MockClient.return_value
            instance.list_buckets.return_value = {"buckets": [], "count": 0}
            fn()

        MockClient.assert_called_once_with(
            access_key_id="env_access_key",
            secret_access_key="env_secret_key",
            region="eu-west-1",
        )


class TestErrorHandling:
    def setup_method(self):
        self.client = _S3Client(
            access_key_id="test_access_key",
            secret_access_key="test_secret_key",
            region="us-east-1",
        )

    def test_client_error_handling(self):
        mcp = MagicMock()
        registered_fns = []
        mcp.tool.return_value = lambda fn: registered_fns.append(fn) or fn

        cred_manager = MagicMock()
        cred_manager.get.side_effect = lambda name: {
            "aws_s3": "test_key",
            "aws_s3_secret": "test_secret",
            "aws_s3_region": None,
        }.get(name)

        register_tools(mcp, credentials=cred_manager)

        fn = next(f for f in registered_fns if f.__name__ == "list_s3_buckets")

        error_response = {"Error": {"Code": "AccessDenied", "Message": "Access Denied"}}
        with patch("aden_tools.tools.aws_s3_tool.aws_s3_tool._S3Client") as MockClient:
            instance = MockClient.return_value
            instance.list_buckets.side_effect = ClientError(error_response, "ListBuckets")
            result = fn()

        assert "error" in result
        assert "AccessDenied" in result["error"]

    def test_no_credentials_error(self):
        mcp = MagicMock()
        registered_fns = []
        mcp.tool.return_value = lambda fn: registered_fns.append(fn) or fn

        cred_manager = MagicMock()
        cred_manager.get.side_effect = lambda name: {
            "aws_s3": "test_key",
            "aws_s3_secret": "test_secret",
            "aws_s3_region": None,
        }.get(name)

        register_tools(mcp, credentials=cred_manager)

        fn = next(f for f in registered_fns if f.__name__ == "list_s3_objects")

        with patch("aden_tools.tools.aws_s3_tool.aws_s3_tool._S3Client") as MockClient:
            instance = MockClient.return_value
            instance.list_objects.side_effect = NoCredentialsError()
            result = fn(bucket_name="my-bucket")

        assert "error" in result
        assert "credentials" in result["error"].lower()


class TestInputValidation:
    def setup_method(self):
        self.mcp = MagicMock()
        self.registered_fns = []
        self.mcp.tool.return_value = lambda fn: self.registered_fns.append(fn) or fn

        cred_manager = MagicMock()
        cred_manager.get.side_effect = lambda name: {
            "aws_s3": "test_key",
            "aws_s3_secret": "test_secret",
            "aws_s3_region": "us-east-1",
        }.get(name)

        register_tools(self.mcp, credentials=cred_manager)
        self.fn_map = {f.__name__: f for f in self.registered_fns}

    def test_list_s3_objects_missing_bucket(self):
        result = self.fn_map["list_s3_objects"](bucket_name="")
        assert "error" in result
        assert "bucket_name" in result["error"]

    def test_list_s3_objects_invalid_max_keys(self):
        result = self.fn_map["list_s3_objects"](bucket_name="my-bucket", max_keys=0)
        assert "error" in result
        assert "max_keys" in result["error"]

    def test_get_s3_object_content_missing_bucket(self):
        result = self.fn_map["get_s3_object_content"](bucket_name="", object_key="file.txt")
        assert "error" in result
        assert "bucket_name" in result["error"]

    def test_get_s3_object_content_missing_key(self):
        result = self.fn_map["get_s3_object_content"](bucket_name="my-bucket", object_key="")
        assert "error" in result
        assert "object_key" in result["error"]


class TestDefaultRegion:
    def test_default_region_us_east_1(self):
        mcp = MagicMock()
        registered_fns = []
        mcp.tool.return_value = lambda fn: registered_fns.append(fn) or fn

        cred_manager = MagicMock()
        cred_manager.get.side_effect = lambda name: {
            "aws_s3": "test_key",
            "aws_s3_secret": "test_secret",
            "aws_s3_region": None,
        }.get(name)

        register_tools(mcp, credentials=cred_manager)

        fn = next(f for f in registered_fns if f.__name__ == "list_s3_buckets")

        with patch("aden_tools.tools.aws_s3_tool.aws_s3_tool._S3Client") as MockClient:
            instance = MockClient.return_value
            instance.list_buckets.return_value = {"buckets": [], "count": 0}
            fn()

        call_kwargs = MockClient.call_args[1]
        assert call_kwargs["region"] == "us-east-1"
