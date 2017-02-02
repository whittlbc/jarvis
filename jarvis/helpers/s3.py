import boto3
from jarvis.helpers.configs import config
from boto3.s3.transfer import S3Transfer

s3 = boto3.client('s3', config('S3_REGION_NAME'))
s3_transfer = S3Transfer(s3)


def download(s3_path, download_path):
	s3_transfer.download_file(config('S3_BUCKET_NAME'), s3_path, download_path)