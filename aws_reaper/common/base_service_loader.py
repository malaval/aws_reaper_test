# Reviewed on October 22

import glob
import importlib
import logging
from os import path

from aws_reaper.common.exceptions import AwsReaperException

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class BaseServiceLoader:
    """
    Base class that implements common attributes and methods for the ServiceModel classes in
    aws_reaper.service_loader and aws_reaper.tests.create_resources.service_loader

    ServiceLoader loads service modules and provides access to module attributes and methods that
    define how each service should be processed.

    """

    def _check_infinite_loop(self, service, resource_type, nb_iteration):
        """
        Args:
            service (str): Name of the service
            resource_type (str): Name of the resource type
            nb_iteration (int): Increment number to count the number of recursion

        Raises:
            AwsReaperException: If there was more than 10 recursions, we consider that there is
            an infinite loop.

        """
        if nb_iteration > 10:
            raise AwsReaperException
        for dependency in self.get_dependencies(service, resource_type):
            d_service, d_resource_type = dependency.split(':')
            self._check_infinite_loop(d_service, d_resource_type, nb_iteration + 1)

    def __init__(self, package_name='aws_reaper.services'):
        """
        Initialize a new BaseServiceLoader object.

        Args:
            package_name (str): Name of the package that contains the service modules. Default
                value is 'aws_reaper.services'.

        """
        # Dynamically find and load service modules
        self._services = {}
        try:
            package_dirname = importlib.import_module(package_name).dirname
            py_files = glob.glob(package_dirname + "/*.py")
            for py_file in py_files:
                if path.isfile(py_file) and not py_file.endswith('_.py'):
                    service = path.basename(py_file)[:-3]
                    module_name = '%s.%s' % (package_name, service)
                    try:
                        self._services[service] = importlib.import_module(module_name).service
                    except Exception:
                        message = 'Unable to load service module %s' % service
                        logger.fatal(message)
                        raise AwsReaperException(message)
        except Exception:
            message = 'Unable to list service modules at %s' % package_name
            logger.fatal(message)
            raise AwsReaperException(message)
        # Check dependencies to ensure that there is no infinite loop with dependencies
        for service, resource_type in self.list_all_resource_types():
            try:
                self._check_infinite_loop(service, resource_type, 1)
            except AwsReaperException:
                message = 'Infinite loop detected with "%s:%s"' % (service, resource_type)
                logger.fatal(message)
                raise AwsReaperException(message)
            except Exception:
                message = 'Unable to find or parse one of "%s:%s" dependencies' % \
                          (service,  resource_type)
                logger.fatal(message)
                raise AwsReaperException(message)

    def list_services(self):
        return self._services.keys()

    def get_service(self, service):
        return self._services[service]

    def list_resource_types(self, service):
        return self._services[service].list_resource_types()

    def list_all_resource_types(self):
        """
        Returns:
            list: List the resource types for all services. Return a list of tuples in the form
                of (service, resource_type)

        """
        result = []
        for service in self.list_services():
            for resource_type in self.list_resource_types(service):
                result.append((service, resource_type))
        return result

    def get_dependencies(self, service, resource_type):
        """
        Args:
            service (str): Name of the service
            resource_type (str): Name of the resource type

        Returns:
            list: List of dependencies in the form of service:resource_type.

        """
        dependencies = self.get_service(service).get_resource_type(resource_type)['Dependencies']
        if dependencies is None:
            return []
        else:
            return dependencies

    def resource_type_exists(self, service, resource_type):
        try:
            self.get_service(service).get_resource_type(resource_type)
            return True
        except KeyError:
            return False
