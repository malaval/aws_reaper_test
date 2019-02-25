import logging
from inspect import isfunction

from aws_reaper.common.exceptions import AwsReaperException
from aws_reaper.config import Config

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class Service:
    """
    Class that is used in service modules.

    """

    def __init__(self, friendly_name=''):
        self._friendly_name = friendly_name
        self._resource_types = {}
        self._allowed_iam_services = []
        self._denied_iam_actions = {}
        self._service_role_names = []

    def list_resource_types(self):
        return self._resource_types.keys()

    def get_resource_type(self, resource_type):
        return self._resource_types[resource_type]

    def add_resource_type(
            self, resource_type, friendly_name, describe, delete, delete_after=None,
            max_wait_until_deleted=Config.MAX_WAIT_UNTIL_DELETED
    ):
        """
        Declare a new resource type for that service.

        Args:
            resource_type (str): Identifier of the resource type. Example = instance
            friendly_name (str): Friendly name of the resource type. Example = EC2 instance
            describe (func): Pointer to the function that lists the resources to delete
            delete (func): Pointer to the function that deletes resources
            delete_after (list): List of resource types that must be deleted after this resource
                type in the form of ``service:resource_type``. Default is None (empty list)
            max_wait_until_deleted (int): Maximum number of seconds to wait for resources of that
                resource type to be deleted. Default is Config.MAX_WAIT_UNTIL_DELETED

        Raises:
            AwsReaperException: If the arguments are invalid

        """
        # Check parameters
        try:
            assert isinstance(resource_type, str) and len(resource_type) > 0
            assert isfunction(describe)
            assert isfunction(delete)
            assert delete_after is None or isinstance(delete_after, list)
            assert isinstance(max_wait_until_deleted, int)
        except Exception:
            message = 'Invalid resource type parameters for %s' % resource_type
            logger.fatal(message)
            raise AwsReaperException(message)

        # Add a dict in self._resource_types
        self._resource_types[resource_type] = {
            'FriendlyName': friendly_name,
            'Describe': describe,
            'Delete': delete,
            'Dependencies': delete_after,
            'MaxWaitUntilDeleted': max_wait_until_deleted
        }

    def add_allowed_iam_service(self, service_name):
        """
        Add a new IAM service that should be allowed (IAM action = service:*).

        Args:
            service_name (str): Name of the IAM service

        """
        if service_name not in self._allowed_iam_services:
            self._allowed_iam_services.append(service_name)

    def add_denied_iam_action(self, service_name, action, reason):
        """
        Add a new IAM action that should be denied.

        Args:
            service_name (str): Name of the IAM service
            action (str): Name of the IAM action. Can contain wildcard characters
            reason (str): Reason why that IAM action should not be allowed

        """
        service_action = '%s:%s' % (service_name, action)
        self._denied_iam_actions[service_action] = reason

    def add_service_role_name(self, service_role_name):
        """
        If a service role (not a service-linked role) is needed to delete resources, specify the
        principal for that service role.

        Args:
            service_role_name (string): Service name role. Can contain wildcard characters.
                Example: lambda.amazonaws.com

        """
        self._service_role_names.append(service_role_name)

    def get_allowed_iam_services(self):
        return self._allowed_iam_services

    def get_denied_iam_actions(self):
        return self._denied_iam_actions

    def get_service_role_names(self):
        return self._service_role_names

    def get_friendly_name(self):
        return self._friendly_name


def simple_describe(client, operation_name, eval_expression, **kwargs):
    """
    Evaluate the string ``eval_expression`` to return a list of AWS resource identifiers from the
    response of the API operation ``operation_name``. We use a paginator if it is supported by
    boto3 for this API operation.

    Args:
        client: boto3 client object.
        operation_name (str): Name of the API operation (e.g. ``describe_instances`` for EC2).
        eval_expression (str): Expression to evaluate to return a list of resource identifiers. The
            response of the API operation is contained in the variable ``data``.
        **kwargs: Arbitrary keyword arguments passed to the boto3 operation.

    Returns:
        list: List of AWS resource identifiers.

    Example:
        The following call returns a list of EBS volume IDs::
        ``simple_describe(client, 'describe_volumes', '[i['VolumeId'] for i in data['Volumes'])``

    """

    if client.can_paginate(operation_name):
        paginator = client.get_paginator(operation_name)
        response = paginator.paginate(**kwargs)
        ids = []
        for data in response:
            ids += eval(eval_expression)

    else:
        data = getattr(client, operation_name)(**kwargs)
        ids = eval(eval_expression)

    return ids
