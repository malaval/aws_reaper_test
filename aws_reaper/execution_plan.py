import logging
import time

from aws_reaper.common.base_execution_plan import BaseExecutionPlan
from aws_reaper.common.exceptions import AwsReaperException

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class ExecutionPlanStep:
    """
    Represent a step in an execution plan defined by a service, a region and a resource type.

    """

    def __init__(self, input_dict=None):
        """
        Create an ExecutionPlanStep object by initializing a new object instance and loading the
        object from a dict.

        Args:
            input_dict (dict): Step content as generated by ``export``

        """
        if input_dict is None:
            self.service = ''
            self.region = ''
            self.resource_type = ''
            self.dependencies = []  # List of dependencies with other steps
            self.status = 'NotStarted'  # Possible values: NotStarted, Ongoing or Completed
            self.start_time = 0
            # Will be populated with the current timestamp when we start processing this step
            self.describe_error = ''  # Will be populated with the error message if describe failed
            self.resource_id_patterns_to_delete = []
            self.resource_id_patterns_to_exclude = []
            self.resource_ids_to_delete = []  # Identifier of resources to delete
            self.resource_ids_deleted = []  # Identifier of resources deleted
            self.resource_ids_excluded = []  # Identifier of resources excluded
            self.resource_ids_failed_to_delete = {}
            # Will contain the identifier of resources that failed to deleted and the related error
            # message
            self.wait_for_deletion_until = 0
            # If a resource is scheduled for deletion, like a KMS CMK, will contain the UTC
            # timestamp when the resource will be effectively deleted. Otherwise, value will
            # remain at 0
        else:
            try:
                self.service = input_dict['Service']
                self.region = input_dict['Region']
                self.resource_type = input_dict['ResourceType']
                self.dependencies = input_dict['DeleteAfter']
                self.status = input_dict['Status']
                self.start_time = input_dict['StartTime']
                self.describe_error = input_dict['DescribeError']
                self.resource_id_patterns_to_delete = input_dict['ResourceIdPatternsToDelete']
                self.resource_id_patterns_to_exclude = input_dict['ResourceIdPatternsToExclude']
                self.resource_ids_to_delete = input_dict['ResourceIdsToDelete']
                self.resource_ids_deleted = input_dict['ResourceIdsDeleted']
                self.resource_ids_excluded = input_dict['ResourceIdsExcluded']
                self.resource_ids_failed_to_delete = input_dict['ResourceIdsFailedToDelete']
                self.wait_for_deletion_until = input_dict['WaitForDeletionUntil']
            except Exception as e:
                message = 'Cannot load step from dict: %s' % str(e)
                logger.fatal(message)
                raise AwsReaperException(message)

    @property
    def step_key(self):
        return str('%s:%s:%s') % (self.service, self.region, self.resource_type)

    def export(self, full=True):
        if full:
            return {
                'Service': self.service,
                'Region': self.region,
                'ResourceType': self.resource_type,
                'DeleteAfter': self.dependencies,
                'Status': self.status,
                'StartTime': self.start_time,
                'DescribeError': self.describe_error,
                'ResourceIdPatternsToDelete': self.resource_id_patterns_to_delete,
                'ResourceIdPatternsToExclude': self.resource_id_patterns_to_exclude,
                'ResourceIdsToDelete': self.resource_ids_to_delete,
                'ResourceIdsDeleted': self.resource_ids_deleted,
                'ResourceIdsExcluded': self.resource_ids_excluded,
                'ResourceIdsFailedToDelete': self.resource_ids_failed_to_delete,
                'WaitForDeletionUntil': self.wait_for_deletion_until
            }
        else:
            return {
                'Service': self.service,
                'Region': self.region,
                'ResourceType': self.resource_type,
                'DeleteAfter': self.dependencies,
            }


class ExecutionPlan(BaseExecutionPlan):
    """
    Inherit from BaseExecutionPlan to create an execution plan that defines what resources to delete
    and in which order.

    """

    def __init__(
            self, loader, step_class=ExecutionPlanStep, override_botocore_regions=False,
            input_dict=None, ignore_dependencies=False
    ):
        """
        Initialize a new ExecutionPlan object.

        Args:
            loader (:obj:`ServiceLoader`): ServiceLoader object
            step_class (obj): Class for plan steps
            override_botocore_regions (bool): For some services, botocore might return an
                incomplete list of regions that a service supports. Set to True to override the
                list of supported regions returned by botocore, and try to delete resources for
                that service in every possible region.
            input_dict (dict): Pass a dict to load the plan from a previous state
            ignore_dependencies (bool): Set to True to ignore dependencies. You can ignore
                dependencies when you describe resources only, not delete them.

        """
        BaseExecutionPlan.__init__(
            self, loader, step_class, override_botocore_regions= override_botocore_regions,
            input_dict=input_dict
        )
        self._ignore_dependencies = ignore_dependencies

    def populate_plan(self, included_patterns, excluded_patterns):
        """
        Populate the execution plan.

        Args:
            included_patterns (list): List of patterns of resources to include in the form of
                A:B:C:D with A "*" of a service name, B "*" or a region name, C "*" or a resource
                type name, D a resource identifier pattern that can contain a wildcard like
                "prefix*. Default is ["*:*:*:*"] to include all possible resources.
            excluded_patterns (): Same as included_patterns but defines the resources to not
                delete. Default is an empty list.

        """
        # Parse included_patterns and excluded_patterns
        try:
            included = [i.split(':', 3) for i in included_patterns]
            excluded = [i.split(':', 3) for i in excluded_patterns]
            assert all(len(i) == 4 for i in included)
            assert all(len(i) == 4 for i in excluded)
        except Exception:
            message = 'Unable to parse included or excluded ID patterns'
            logger.fatal(message)
            raise AwsReaperException(message)

        for service in self._loader.list_services():
            for resource_type in self._loader.list_resource_types(service):
                for region in self.get_regions_for_service(service):

                    # Skip if (service, region and resource_type) matches one of the
                    # excluded_patterns
                    if any(
                        e_service in ('*', service)
                        and e_region in ('*', region)
                        and e_resource_type in ('*', resource_type) and e_resource_id_pattern == '*'
                        for e_service, e_region, e_resource_type, e_resource_id_pattern
                        in excluded
                    ):
                        continue

                    # Continue only if (service, region and resource_type) matches at least one
                    # included_patterns
                    if not any(
                        i_service in ('*', service)
                        and i_region in ('*', region)
                        and i_resource_type in ('*', resource_type)
                        for i_service, i_region, i_resource_type, i_resource_id_pattern
                        in included
                    ):
                        continue

                    # Find included_patterns that match (service, region and resource_type) and
                    # consolidate resource identifier patterns
                    i_patterns = [
                        i_resource_id_pattern
                        for i_service, i_region, i_resource_type, i_resource_id_pattern
                        in included
                        if i_service in ('*', service)
                        and i_region in ('*', region)
                        and i_resource_type in ('*', resource_type)
                    ]

                    # Find included_patterns that match (service, region and resource_type) and
                    # consolidate resource identifier patterns
                    e_patterns = [
                        e_resource_id_pattern
                        for e_service, e_region, e_resource_type, e_resource_id_pattern
                        in excluded
                        if e_service in ('*', service)
                        and e_region in ('*', region)
                        and e_resource_type in ('*', resource_type)
                    ]

                    # Skip if at least one resource ID pattern excludes all resources for (service,
                    # region and resource_type)
                    if '*' in e_patterns:
                        continue

                    # Add a step into the execution plan
                    step = self.add_step(service, region, resource_type)
                    step.resource_id_patterns_to_delete = i_patterns
                    step.resource_id_patterns_to_exclude = e_patterns

    def get_next_step(self):
        """
        Return the next step to process.

        Returns:
            step_key: Step key to process, ``wait`` if the ongoing steps must complete before
                the remaining steps can be processed, or ``end`` if no other step has to
                be processed.
            step: ExecutionPlanStep object to process, or None if step_key is ``wait`` or
                ``end``

        """
        # If dependencies are ignored, return the first step that is not yet started.
        if self._ignore_dependencies:
            for step_key, step in self._steps.items():
                if step.status == 'NotStarted':
                    # Set start time if it is the first time that the step is being run
                    step.status = 'Ongoing'
                    if step.start_time == 0:
                        step.start_time = int(time.time())
                    return step_key, step

        else:
            # If a step has not yet started, check if all its dependencies are completed before
            # processing the step.
            for step_key, step in self._steps.items():
                if step.status == 'NotStarted':
                    if not any(
                        step_key in d_step.dependencies and d_step.status != 'Completed'
                        for d_step in self._steps.values()
                    ):
                        # Set start time if it is the first time that the step is being run
                        step.status = 'Ongoing'
                        if step.start_time == 0:
                            step.start_time = int(time.time())
                        return step_key, step

            # Return "wait" if there are steps to process but dependencies are not yet completed.
            if any(step.status == 'NotStarted' for step in self._steps.values()):
                return 'wait', None

        # If the function hasn't returned yet, there is no more step to process, so we return None.
        return 'end', None