import logging
import time

from aws_reaper.common.main import get_aws_account_id
from aws_reaper.config import Config
from aws_reaper.execution_plan import ExecutionPlan
from aws_reaper.execution_worker import ExecutionWorker
from aws_reaper.execution_manager import CheckExecutionManager, CleanExecutionManager
from aws_reaper.service_loader import ServiceLoader
from aws_reaper.common.exceptions import AwsReaperException

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

loader = ServiceLoader()


class Reaper:

    def __init__(
            self, included_id_patterns=None, excluded_id_patterns=None,
            override_botocore_regions=False, nb_workers=Config.CONCURRENT_WORKERS,
            **credentials
    ):
        """
        Initialize a new Reaper object.

        Args:
            included_id_patterns (list): List of patterns of resources to include in the form of
                A:B:C:D with A "*" of a service name, B "*" or a region name, C "*" or a
                resource type name, D a resource identifier pattern that can contain a wildcard like
                "prefix*. Default is ["*:*:*:*"] to include all possible resources.
            excluded_id_patterns (list): List of patterns of resources to exclude in the form of
                A:B:C:D with A "*" of a service name, B "*" or a region name, C "*" or a
                resource type name, D a resource identifier pattern that can contain a wildcard like
                "prefix*. Default is [] to exclude no resources.
            override_botocore_regions: For some services, botocore might return an incomplete
                list of regions that a service supports. Set to True to override the list of
                supported regions returned by botocore, and try to delete resources for that
                service in every possible region. Default is False.
            nb_workers (int): Number of concurrent threads that are processing the execution
                plan.
            **credentials: Keyword arguments used as AWS credentials

        """
        # Load resource ID patterns
        if included_id_patterns is not None:
            self.included_id_patterns = included_id_patterns
        else:
            self.included_id_patterns = ['*:*:*:*']
        if excluded_id_patterns is not None:
            self.excluded_id_patterns = excluded_id_patterns
        else:
            self.excluded_id_patterns = []

        # Load credentials
        keys = ('aws_access_key_id', 'aws_secret_access_key', 'aws_session_token', 'profile_name')
        if len(credentials) == 0 or not all(i in keys for i in credentials):
            message = 'Please provide valid AWS credentials'
            logger.critical(message)
            raise AwsReaperException(message)
        self.credentials = credentials

        self.override_botocore_regions = override_botocore_regions
        self.worker = ExecutionWorker(loader, nb_workers, **credentials)
        self.account_id = get_aws_account_id(self.credentials)

    def _generate_execution_plan(self, ignore_dependencies=False):
        plan = ExecutionPlan(
            loader, ignore_dependencies=ignore_dependencies,
            override_botocore_regions=self.override_botocore_regions
        )
        plan.populate_plan(self.included_id_patterns, self.excluded_id_patterns)
        return plan

    def get_execution_plan(self):
        """
        Generates and returns an execution plan that describes what AWS resources to delete and
        in which order.

        Returns:
            list: List in the form of ::
                [
                    {
                        "Service": service,
                        "ResourceType": resource type,
                        "Region": region,
                        "DeleteAfter": list of resource types that must be deleted after the
                            current resource type
                    }
                ]

        """
        try:
            plan = self._generate_execution_plan()
            return plan.export(full=False)
        except Exception as e:
            message = 'Failed to generate the execution plan: %s' % e
            logger.fatal(message, exc_info=True)
            raise AwsReaperException(message)

    def check_account(self, state=None, timeout=None):
        """
        Check if there are resources to delete in the AWS account.

        Args:
            state (dict): If the previous execution of ``check_account`` was interrupted, you should
                pass the response of the previous call (``State``).
            timeout (int): If timeout is set, the function will be interrupted when ``timeout``
                seconds have elapsed. If some steps remain to complete, the function will return
                a snapshot of the execution plan and it can be passed as an argument of a next
                call to ``check_account``. This is particularly useful for AWS Lambda.

        Returns:
            dict: Dictionary structured as follows, if the execution plan was completed::

                {
                    'Completed': True,
                    'ResourceIdsToDelete': {
                        'service:region-resource-type': ['ResourceId'],
                        ...
                    },
                    'ResourceIdsExcluded' (dict): {
                        'service:region-resource-type': ['ResourceId'],
                        ...
                    },
                    'Errors': {
                        'Describe': {
                            'service:region-resource-type': 'ErrorMessage',
                            ...
                        }
                    }
                }

            Otherwise, if the execution was interrupted::

                {
                    'Completed': False,
                    'State': {
                        'ExecutionId': UUID for the current execution,
                        'CurrentPlan': Snapshot of the execution plan (dict)
                    }
                }

        """
        if state is None:
            init_plan = self._generate_execution_plan(ignore_dependencies=True)
            manager = CheckExecutionManager(loader, init_plan=init_plan)
        else:
            manager = CheckExecutionManager(loader, state=state)

        plan = manager.get_plan()
        try:
            plan_completed = self.worker.run_describe(
                plan, timeout=timeout, aws_account_id=self.account_id
            )
        except KeyboardInterrupt:
            return {'Completed': False}

        # If the execution plan is completed
        if plan_completed:
            # Initialize the result dict
            result = {
                'Completed': True,
                'ResourceIdsToDelete': {},
                'ResourceIdsExcluded': {},
                'Errors': {
                    'Describe': {}
                }
            }
            for step_key, step in plan.get_steps().items():
                # Populate with resources to delete for this step
                if len(step.resource_ids_to_delete) > 0:
                    result['ResourceIdsToDelete'][step_key] = sorted(step.resource_ids_to_delete)
                # Populate with resources that failed to delete for this step
                if len(step.resource_ids_excluded) > 0:
                    result['ResourceIdsExcluded'][step_key] = sorted(step.resource_ids_excluded)
                # If the step failed to describe the resources
                if step.describe_error != '':
                    if not (
                        self.override_botocore_regions
                        and 'EndpointConnectionError' in step.describe_error
                    ):
                        result['Errors']['Describe'][step_key] = step.describe_error
            return result

        # If the execution plan is not completed
        else:
            return {
                'Completed': False,
                'State': manager.export_to_dict()
            }

    def clean_account(
            self, state=None, timeout=None, min_passes=Config.MIN_PASSES,
            max_passes=Config.MAX_PASSES
    ):
        """
        Delete the resources contained in the AWS account.

        Args:
            state (dict): If the previous execution of ``clean_account`` was interrupted, you should
                pass the response of the previous call (``State``).
            timeout (int): If timeout is set, the function will be interrupted when ``timeout``
                seconds have elapsed. If some steps remain to complete, the function will return
                a snapshot of the execution state and it can be passed as an argument of a next
                call to ``clean_account``. This is particularly useful for AWS Lambda.
            min_passes (int): The minimum number of times that the reaper script will run over
                the account and try to delete resources.
            max_passes (int): The reaper script will be run over the account at least
                ``min_passes`` times and stop aither when no new resources are deleted or failed to
                delete during a pass or when the maximum number of passes ``max_passes`` is
                reached.

        Returns:
            dict: Dictionary structured as follows, if the cleaning execution was completed::

                {
                    'Completed' (bool): True,
                    'ResourceIdsDeleted': {
                        'service:region-resource-type': ['ResourceId'],
                        ...
                    },
                    'ResourceIdsExcluded': {
                        'service:region-resource-type': ['ResourceId'],
                        ...
                    },
                    'Errors': {
                        'Describe': {
                            'service:region-resource-type': 'ErrorMessage',
                            ...
                        },
                        'Delete': {
                            'service:region-resource-type': {
                                'ResourceId': 'ErrorMessage',
                                ...
                            },
                            ...
                        }
                    },
                    'WaitForDeletionUntil': If a resource is scheduled for deletion, like a KMS
                        CMK or a private CA, contains a UTC timestamp when the resource will be
                        effectively deleted. Otherwise, value is 0.
                }

            Otherwise, if the execution was interrupted::

                {
                    'Completed' (bool): False,
                    'State' (dict): Current state
                }

        """
        # Initialize the execution manager
        if state is None:
            init_plan = self._generate_execution_plan()
            manager = CleanExecutionManager(
                loader, init_plan=init_plan, min_passes=min_passes, max_passes=max_passes
            )
        else:
            manager = CleanExecutionManager(
                loader, state=state, min_passes=min_passes, max_passes=max_passes
            )

        all_completed = False
        current_plan = None
        start_time = time.time()

        while True:
            # Get the next execution plan to process
            next_plan = manager.get_next_plan()
            # get_next_plan returns None if no more pass is needed
            if next_plan is None:
                all_completed = True
                break
            # If another pass is needed, execute the plan
            else:
                current_plan = next_plan
                if timeout is not None:
                    pass_timeout = int(timeout - (time.time() - start_time))
                else:
                    pass_timeout = None
                try:
                    plan_completed = self.worker.run_describe_and_delete(
                        current_plan, timeout=pass_timeout, aws_account_id=self.account_id
                    )
                except KeyboardInterrupt:
                    return {'Completed': False}
                if not plan_completed:
                    break

        # If the execution passes are completed
        if all_completed:
            # Initialize the result dict
            result = {
                'Completed': True,
                'ResourceIdsDeleted': {},
                'ResourceIdsExcluded': {},
                'Errors': {
                    'Describe': {},
                    'Delete': {}
                },
                'WaitForDeletionUntil': 0
            }
            for step_key, step in current_plan.get_steps().items():
                # Populate with resources deleted for this step
                if len(step.resource_ids_deleted) > 0:
                    result['ResourceIdsDeleted'][step_key] = \
                        sorted(step.resource_ids_deleted)
                # Populate with resources that failed to delete for this step
                if len(step.resource_ids_excluded) > 0:
                    result['ResourceIdsExcluded'][step_key] = \
                        sorted(step.resource_ids_excluded)
                # If the step failed because it could not describe resources
                if step.describe_error != '':
                    # Ignore endpoint error if override_botocore_regions is True
                    if not (
                        self.override_botocore_regions
                        and 'EndpointConnectionError' in step.describe_error
                    ):
                        result['Errors']['Describe'][step_key] = step.describe_error
                for error_key, error_msg in step.resource_ids_failed_to_delete.items():
                    # Ignore endpoint error if override_botocore_regions is True
                    if not (
                        self.override_botocore_regions
                        and 'EndpointConnectionError' in error_msg
                    ):
                        result['Errors']['Delete'].setdefault(step_key, {})
                        result['Errors']['Delete'][step_key][error_key] = error_msg
                if step.wait_for_deletion_until > 0:
                    if step.wait_for_deletion_until > result['WaitForDeletionUntil']:
                        result['WaitForDeletionUntil'] = int(step.wait_for_deletion_until)
            return result

        else:
            return {
                'Completed': False,
                'State': manager.export_to_dict()
            }

    @staticmethod
    def list_supported_resource_types():
        return sorted(['%s:%s' % (i[0], i[1]) for i in loader.list_all_resource_types()])
