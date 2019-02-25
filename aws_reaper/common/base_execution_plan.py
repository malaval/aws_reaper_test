import copy
import logging

import botocore.session
import botocore.regions
import botocore.exceptions

from aws_reaper.common.exceptions import AwsReaperException

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class BaseExecutionPlan:
    """
    Base class that implements common attributes and methods for the ExecutionPlan classes in
    aws_reaper.execution_plan and aws_reaper.tests.create_resources.execution_plan

    An execution plan defines what resources should be processed in an AWS account and what
    dependencies exist between resources.

    """

    def __init__(self, loader, step_class, override_botocore_regions=False, input_dict=None):
        """
        Create a BaseExecutionPlan object either by initializing a new object instance or by
        loading data from a dict.

        Args:
            loader (:obj:`ServiceLoader`): ServiceLoader object
            step_class (obj): Class for plan steps
            override_botocore_regions (bool): For some services, botocore might return an
                incomplete list of regions that a service supports. Set to True to override the
                list of supported regions returned by botocore, and try to delete resources for
                that service in every possible region.
            input_dict (dict): Pass a dict to create a plan from it. Default is None to create a
                new plan instance.

        """
        self._session = botocore.session.get_session()
        self._loader = loader
        self._step_class = step_class
        self._override_botocore_regions = override_botocore_regions
        self._steps = {}  # Contains plan steps
        self._partition = 'aws'
        # If a dict is provided to preload the execution plan
        if input_dict is not None:
            try:
                # Create a copy of the dict to avoid keeping unexpected references
                copy_dict = copy.deepcopy(input_dict)
                for step_key, step_dict in copy_dict.items():
                    step = self._step_class(input_dict=step_dict)
                    self._steps[step_key] = step
            except Exception:
                message = 'Unable to load execution plan from dict'
                logger.fatal(message)
                raise AwsReaperException(message)

    def get_steps(self):
        return self._steps

    def _is_global_service(self, service):
        """
        Args:
            service (str): Name of the service.

        Returns:
            bool: Return True if that service is a global service.

        """
        try:
            endpoint_data = self._session.get_data('endpoints')
            resolver = botocore.regions.EndpointResolver(endpoint_data)
            resolver.construct_endpoint(service)
        # The resolver raises a NoRegionError exception if the service is regionalized because we
        # don't provide a region name
        except botocore.exceptions.NoRegionError:
            return False
        else:
            return True

    def _get_global_region(self):
        """
        Returns:
            str: Name of the region that must be used for global services

        """
        if self._partition == 'aws':
            return 'us-east-1'

    def get_regions_for_service(self, service):
        """
        Args:
            service (str): Name of the service.

        Returns:
            list: If self._override_botocore_regions is False, returns the list of regions where
                that service is supported or ['us-east-1'] if that service is a global service. If
                self._override_botocore_regions is True, returns all of the available regions or [
                'us-east-1'] if that service is a global service.

        """
        if self._is_global_service(service):
            return [self._get_global_region()]
        else:
            if self._override_botocore_regions:
                # We consider that EC2 is supported in all possible regions so
                # get_available_regions('ec2') should return the list of all existing regions
                return self._session.get_available_regions('ec2')
            else:
                return self._session.get_available_regions(service)

    def step_exists(self, service, region, resource_type):
        """
        Args:
            service (str): Name of the service.
            region (str): Name of the region.
            resource_type (str): Name of the resource type.

        Returns:
            bool: Return True if a step for (service, region, resource_type) already exists in
                the execution plan.

        """
        step_key = '%s:%s:%s' % (service, region, resource_type)
        return step_key in self._steps

    def add_step(self, service, region, resource_type):
        """
        Base function that adds a new step in the execution plan, and adapt its dependencies to
        the current region. For example, if 'ec2:instance' is dependent with 'ec2:volume', then
        'ec2:us-east-1:instance' is dependent with 'ec2:us-east-1:volume'

        Args:
            service (str): Name of the service
            region (str): Name of the region
            resource_type (str): Name of the resource type

        Returns:
            obj: Object inheriting from the class self._class_step

        """
        step = self._step_class()
        step.service = service
        step.region = region
        step.resource_type = resource_type
        try:
            dependencies = self._loader.get_dependencies(service, resource_type)
        except Exception:
            message = '"%s:%s" was not found in the service modules' % (service, resource_type)
            logger.fatal(message)
            raise AwsReaperException(message)
        # Process each of the dependencies
        for dependency in dependencies:
            d_service, d_resource_type = dependency.split(':')
            # If d_service is a global service, then d_region is 'us-east-1' whatever the value
            # of region
            if self._is_global_service(d_service):
                d_region = self._get_global_region()
            else:
                # If d_service is not a global service, check if d_service is supported in
                # region. Skip the dependency if d_service is not supported in the region.
                if region not in self.get_regions_for_service(d_service):
                    continue
                else:
                    d_region = region
            step.dependencies.append('%s:%s:%s' % (d_service, d_region, d_resource_type))
        self._steps[step.step_key] = step
        return step

    def export(self, full=True):
        """
        Exports the execution plan.

        Args:
            full (bool): True if the dict must contain the attributes that are needed to
                execute the plan, False to export only the values that are needed for someone to
                understand the relationships between AWS resources to delete.

        Returns:
            dict: If full is True, dict in the form of::
                {
                    "step_key": step.export(),
                    ...
                }
            list: If full is False, list in the form of::
                [
                    step.export(),
                    ...
                ]

        """
        if full:
            return {step_key: step.export() for step_key, step in self._steps.items()}
        else:
            return [step.export(full=False) for step_key, step in self._steps.items()]

    def reset_ongoing_status(self):
        """
        Set status to NotStarted for steps that were ongoing.

        """
        for step in self._steps.values():
            if step.status == 'Ongoing':
                step.status = 'NotStarted'

    def count_remaining_steps(self):
        """
        Returns:
            int: Number of steps that are not yet started.

        """
        result = 0
        for step in self._steps.values():
            if step.status == 'NotStarted':
                result += 1
        return result

    def copy(self):
        """
        Create and return a copy of the execution plan. Step status is reset to ``NotStarted``.

        Returns:
            obj: Copy of the execution plan

        """
        plan_copy = self.__class__(self._loader, self._step_class, input_dict=self.export())
        for step in plan_copy._steps.values():
            step.status = 'NotStarted'
        return plan_copy
