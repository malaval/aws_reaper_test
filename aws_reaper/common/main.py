# Common methods that are used by ``aws_reaper.main`` and
# ``aws_reaper.tests.create_resources.main``.


import logging

import boto3

from aws_reaper.common.exceptions import AwsReaperException

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


def get_aws_account_id(credentials):
    """
    Retrieve the AWS account ID to which belong the provided AWS credentials, using the STS
    GetCallerIdentity API.

    Args:
        credentials (dict): AWS credentials passed to the ``boto3._session.Session`` constructor
            method.

    Returns:
        str: AWS account ID.

    """
    try:
        session = boto3.session.Session(**credentials)
        sts = session.client('sts', region_name='us-east-1')
        account_id = sts.get_caller_identity()['Account']
        logger.debug('Retrieved AWS account ID: %s' % account_id)
        return account_id
    except Exception:
        message = 'Unable to retrieve the AWS account ID'
        logger.fatal(message, exc_info=True)
        raise AwsReaperException(message)
