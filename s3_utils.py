import boto3
import os
from botocore.exceptions import ClientError
import uuid
from datetime import datetime


class S3Uploader:
    def __init__(
        self, access_key_id, secret_access_key, bucket_name, region="us-east-1"
    ):
        self.s3_client = boto3.client(
            "s3",
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            region_name=region,
        )
        self.bucket_name = bucket_name

    def upload_video(self, local_file_path, user_id=None, job_id=None):
        """
        Upload a video file to S3 with user association

        Args:
            local_file_path: Path to the local video file
            user_id: User ID to associate with the upload
            job_id: Optional job ID to include in the filename

        Returns:
            dict: Contains 'success' (bool), 'url' (str), 's3_key' (str), 'error' (str)
        """
        try:
            # Generate unique filename with user context
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_id = str(uuid.uuid4())[:8]

            # Create user-specific folder structure
            if user_id:
                filename = f"users/{user_id}/renders/{timestamp}_{unique_id}"
            else:
                filename = f"renders/{timestamp}_{unique_id}"

            if job_id:
                filename += f"_job_{job_id}"
            filename += ".mp4"

            # Upload file to S3 (private by default, use pre-signed URLs for access)
            self.s3_client.upload_file(
                local_file_path,
                self.bucket_name,
                filename,
                ExtraArgs={"ContentType": "video/mp4"},
            )

            # Generate pre-signed URL for access (7 days)
            presigned_url = self.s3_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket_name, "Key": filename},
                ExpiresIn=604800,  # 7 days
            )

            return {
                "success": True,
                "url": presigned_url,  # Use pre-signed URL as primary URL
                "presigned_url": presigned_url,  # Same URL for consistency
                "s3_key": filename,
                "error": None,
            }

        except ClientError as e:
            return {
                "success": False,
                "url": None,
                "presigned_url": None,
                "s3_key": None,
                "error": str(e),
            }
        except Exception as e:
            return {
                "success": False,
                "url": None,
                "presigned_url": None,
                "s3_key": None,
                "error": str(e),
            }

    def upload_video_for_user(self, local_file_path, user_id, job_id=None):
        """
        Convenience method to upload video specifically for a user

        Args:
            local_file_path: Path to the local video file
            user_id: User ID to associate with the upload
            job_id: Optional job ID to include in the filename

        Returns:
            dict: Contains upload result with user context
        """
        return self.upload_video(local_file_path, user_id, job_id)

    def get_user_videos(self, user_id, prefix=None):
        """
        List all videos for a specific user

        Args:
            user_id: The user ID to get videos for
            prefix: Optional additional prefix

        Returns:
            list: List of video objects for the user
        """
        try:
            user_prefix = f"users/{user_id}/renders/"
            if prefix:
                user_prefix += prefix

            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name, Prefix=user_prefix
            )
            return response.get("Contents", [])
        except ClientError:
            return []

    def delete_user_video(self, user_id, s3_key):
        """
        Delete a video file for a specific user

        Args:
            user_id: The user ID
            s3_key: The S3 key of the file to delete

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Verify the file belongs to the user
            if not s3_key.startswith(f"users/{user_id}/"):
                return False

            self.s3_client.delete_object(Bucket=self.bucket_name, Key=s3_key)
            return True
        except ClientError:
            return False

    def delete_video(self, s3_key):
        """
        Delete a video file from S3

        Args:
            s3_key: The S3 key of the file to delete

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=s3_key)
            return True
        except ClientError:
            return False

    def list_videos(self, prefix="renders/"):
        """
        List all videos in the S3 bucket

        Args:
            prefix: Prefix to filter files

        Returns:
            list: List of video objects
        """
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name, Prefix=prefix
            )
            return response.get("Contents", [])
        except ClientError:
            return []

    def generate_presigned_url(self, s3_key, expires_in=86400):
        """
        Generate a new pre-signed URL for an existing S3 object

        Args:
            s3_key: The S3 key of the file
            expires_in: URL expiration time in seconds (default: 24 hours)

        Returns:
            str: Pre-signed URL or None if failed
        """
        try:
            presigned_url = self.s3_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket_name, "Key": s3_key},
                ExpiresIn=expires_in,
            )
            return presigned_url
        except ClientError:
            return None


def create_s3_uploader():
    """
    Create S3 uploader instance using environment variables

    Returns:
        S3Uploader instance or None if credentials not available
    """
    access_key = os.getenv("AWS_ACCESS_KEY_ID")
    secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    bucket_name = os.getenv("S3_BUCKET_NAME")

    if not all([access_key, secret_key, bucket_name]):
        print(
            "Warning: AWS credentials or bucket name not found in environment variables"
        )
        return None

    return S3Uploader(access_key, secret_key, bucket_name)
