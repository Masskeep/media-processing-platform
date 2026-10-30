import os

from botocore.config import Config
import boto3

AWS_REGION = os.getenv("AWS_REGION", "ap-south-1")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")

s3_client = boto3.client(
    "s3",
    region_name = AWS_REGION,
    config = Config(
        s3 = {"addressing_style": "virtual"},
    )
)

def generate_upload_url(object_key, content_type):
    if not S3_BUCKET_NAME:
        raise ValueError("S3_BUCKET_NAME is missing from the environment")
    presigned_url = s3_client.generate_presigned_url(
        ClientMethod = "put_object",
        Params = {
            "Bucket": S3_BUCKET_NAME,
            "Key": object_key,
            "ContentType": content_type
        },
        ExpiresIn = 300
    )

    return presigned_url


def initiate_multipart_upload(object_key, content_type):
    if not S3_BUCKET_NAME:
        raise ValueError("S3_BUCKET_NAME is missing from the environment")

    response = s3_client.create_multipart_upload(
        Bucket=S3_BUCKET_NAME,
        Key=object_key,
        ContentType=content_type,
    )
    return response["UploadId"]


def generate_part_upload_url(object_key, upload_id, part_number):
    if not S3_BUCKET_NAME:
        raise ValueError("S3_BUCKET_NAME is missing from the environment" )

    if (
        not isinstance(part_number, int)
        or isinstance(part_number, bool)
        or part_number < 1
        or part_number > 10000
    ):
        raise ValueError("part_number must be an integer between 1 and 10000")

    presigned_url = s3_client.generate_presigned_url(
        ClientMethod = "upload_part",
        Params = {
            "Bucket": S3_BUCKET_NAME,
            "Key": object_key,
            "UploadId": upload_id,
            "PartNumber": part_number
        },
        ExpiresIn = 300
    )

    return presigned_url


def abort_multipart_upload(object_key, upload_id):
    if not S3_BUCKET_NAME:
        raise ValueError("S3_BUCKET_NAME is missing from the environment")

    s3_client.abort_multipart_upload(
        Bucket=S3_BUCKET_NAME,
        Key=object_key,
        UploadId=upload_id,
    )

def complete_multipart_upload(object_key, upload_id, parts):
    if not S3_BUCKET_NAME:
        raise ValueError("S3_BUCKET_NAME is missing from the environment")

    response = s3_client.complete_multipart_upload(
        Bucket = S3_BUCKET_NAME,
        Key = object_key,
        UploadId = upload_id,
        MultipartUpload = {
            "Parts": parts
        },
    )

    return response