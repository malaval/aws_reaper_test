import logging
from inspect import isfunction

from aws_reaper.common.exceptions import AwsReaperException

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class Service:
    """
    Class that is used in service modules.

    """

    def __init__(self):
        self._resource_types = {}

    def list_resource_types(self):
        return self._resource_types.keys()

    def get_resource_type(self, resource_type):
        return self._resource_types[resource_type]

    def add_resource_type(
            self, resource_type, create, create_before=None
    ):
        """
        Declare a new resource type for that service.

        Args:
            resource_type (str): Identifier of the resource type. Example = instance
            create (func): Pointer to the function that create resources
            create_before (list): List of resource types that must be created before this resource
                type in the form of ``service:resource_type``. Default is None (empty list)

        Raises:
            AwsReaperException: If the arguments are invalid

        """
        # Check parameters
        try:
            assert isinstance(resource_type, str) and len(resource_type) > 0
            assert isfunction(create)
            assert create_before is None or isinstance(create_before, list)
        except Exception:
            message = 'Invalid resource type parameters for %s' % resource_type
            logger.fatal(message)
            raise AwsReaperException(message)

        # Add a dict in self._resource_types
        self._resource_types[resource_type] = {
            'Create': create,
            'Dependencies': create_before
        }
