import logging

from aws_reaper.common.main import get_aws_account_id
from aws_reaper.config import Config
from aws_reaper.tests.create_resources.execution_plan import ExecutionPlan
from aws_reaper.tests.create_resources.execution_worker import ExecutionWorker
from aws_reaper.tests.create_resources.service_loader import ServiceLoader
from aws_reaper.tests.create_resources.execution_manager import CreateExecutionManager
from aws_reaper.common.exceptions import AwsReaperException

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

loader = ServiceLoader()


class Creator:

    def __init__(
            self, included=None, nb_workers=Config.CONCURRENT_WORKERS, **credentials
    ):
        """
        Initialize a new Creator object.

        Args:
            included (list): List of patterns of resources to include in the form of A:B:C
                with A "*" of a service name, B "*" or a region name, C "*" or a resource type
                name. Default is ["*:*:*"] to create all possible resources.
            nb_workers (int): Number of concurrent threads that are processing the execution
                plan.
            **credentials: Keyword arguments used as AWS credentials

        """
        # Load resource patterns
        if included is not None:
            self.included = included
        else:
            self.included = ['*:*:*']

        # Load credentials
        keys = ('aws_access_key_id', 'aws_secret_access_key', 'aws_session_token', 'profile_name')
        if len(credentials) == 0 or not all(i in keys for i in credentials):
            raise ValueError('Please provide valid AWS credentials')
        self.credentials = credentials

        self.worker = ExecutionWorker(loader, nb_workers, **credentials)
        self.account_id = get_aws_account_id(self.credentials)

    def _generate_execution_plan(self):
        plan = ExecutionPlan(loader)
        plan.populate_plan(self.included)
        return plan

    def get_execution_plan(self):
        """
        Generates and returns an execution plan that describes what AWS resources to create and
        in which order.

        Returns:
            list: List in the form of ::
                [
                    {
                        "Service": service,
                        "ResourceType": resource type,
                        "Region": region,
                        "CreateBefore": list of resource types that must be created before the
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

    def create_resources(self, state=None, timeout=None):
        """
        Process the execution plan to create test resources.

        Args:
            state (dict): If the previous execution of ``create_resources`` was interrupted,
                you should pass the response of the previous call (``State``).
            timeout (int): If timeout is set, the function will be interrupted when ``timeout``
                seconds have elapsed. If some steps remain to complete, the function will return
                a snapshot of the execution plan and it can be passed as an argument of a next
                call to ``create_resources``. This is particularly useful for AWS Lambda.

        Returns:
            dict: Dictionary structured as follows, if the execution plan was completed::

                {
                    'Completed': True,
                    'ResourcesCreated': {
                        'service:region:resource-type': {
                            'ResourceName': 'ResourceId',
                            ...
                        },
                        ...
                    },
                    'Errors': {
                        'Create': {
                            'service:region:resource-type': 'ErrorMessage',
                            ...
                        }
                    }
                }

            Otherwise, if the execution was interrupted::

                {
                    'Completed': False,
                    'State': Current state
                }

        """
        # Initialize the execution manager
        if state is None:
            init_plan = self._generate_execution_plan()
            manager = CreateExecutionManager(loader, init_plan=init_plan)
        else:
            manager = CreateExecutionManager(loader, state=state)

        plan = manager.get_plan()
        try:
            plan_completed = self.worker.run_create(
                plan, timeout=timeout, aws_account_id=self.account_id
            )
        except KeyboardInterrupt:
            return {'Completed': False}

        if plan_completed:
            result = {
                'Completed': True,
                'ResourcesCreated': {},
                'Errors': {
                    'Create': {}
                }
            }
            for step in plan.get_steps().values():
                step_key = step.step_key
                if step.create_error != '':
                    result['Errors']['Create'][step_key] = step.create_error
                    continue
                for r_created_key, r_created_value in step.resources_created.items():
                    result['ResourcesCreated'].setdefault(step_key, {})
                    result['ResourcesCreated'][step_key][r_created_key] = r_created_value
            return result

        # If the execution plan is not completed
        else:
            return {
                'Completed': False,
                'State': manager.export_to_dict()
            }

    @staticmethod
    def list_supported_resource_types():
        return sorted(['%s:%s' % (i[0], i[1]) for i in loader.list_all_resource_types()])
