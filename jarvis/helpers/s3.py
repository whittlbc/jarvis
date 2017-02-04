import boto3
from jarvis.helpers.configs import config
from boto3.s3.transfer import S3Transfer


s3 = boto3.client('s3', config('S3_REGION_NAME'))
s3_transfer = S3Transfer(s3)
bucket_name = config('S3_BUCKET_NAME')


def download(s3_path, download_path):
	s3_transfer.download_file(bucket_name, s3_path, download_path)
	

def upload(local_file_path, s3_path):
	s3_transfer.upload_file(local_file_path, bucket_name, s3_path)
