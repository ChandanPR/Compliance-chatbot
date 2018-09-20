import data
import boto3


class S3(object):
    """
    Creates a AWS S3 Client with AWS_ACCESS_ID and AWS_ACCESS_KEY configuration from database
    """

    def __init__(self):
        aws_access_id = data.get_configuration('AWS_ACCESS_ID')
        aws_access_key = data.get_configuration('AWS_ACCESS_KEY')
        self.s3_client = None
        if aws_access_id and aws_access_key:
            self.s3_client = boto3.resource('s3', aws_access_key_id=aws_access_id
                                            , aws_secret_access_key=aws_access_key)
