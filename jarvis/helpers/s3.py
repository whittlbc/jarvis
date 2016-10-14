from configs import configs
import boto3


s3 = boto3.client(
	's3',
	aws_access_key_id=configs.AWS_ACCESS_KEY_ID,
	aws_secret_access_key=configs.AWS_SECRET_KEY_ID
)
