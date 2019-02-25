from aws_reaper.common.base_service_loader import BaseServiceLoader


class ServiceLoader(BaseServiceLoader):
    """
    Load the service modules and provides methods to easily access their content.

    """

    def __init__(self, package_name='aws_reaper.tests.create_resources.services'):
        BaseServiceLoader.__init__(self, package_name)

    def create(self, service, resource_type):
        """
        Args:
            service (str): Name of the service.
            resource_type (str): Name of the resource type.

        Returns:
            function: Return the function in Create

        """
        return self.get_service(service).get_resource_type(resource_type)['Create']
