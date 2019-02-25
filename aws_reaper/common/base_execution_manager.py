import logging
import uuid

from aws_reaper.common.exceptions import AwsReaperException

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class BaseExecutionManager:
    """
    Base class that implements common attributes and methods for the ExecutionManager classes in
    aws_reaper.execution_manager and aws_reaper.tests.create_resources.execution_manager

    An execution manager is used to stop and resume an execution, and to manage execution plans
    when multiple passes are needed.

    """

    def __init__(self, loader, plan_class, init_plan=None, state=None):
        """
        Create a new execution manager.

        Args:
            loader (:obj:`ServiceLoader`): ServiceLoader object
            plan_class (obj): Class for execution plan
            init_plan (obj): Initial execution plan
            state (dict): Provide a dict to preload the execution manager from a previous state.
                Do not provide a value for ``init_plan`` if you pass a value to ``state``

        """
        self._loader = loader
        # If a previous state is provided
        if state is None:
            self._execution_id = str(uuid.uuid4())
            self._plan = init_plan
        # Otherwise create a new object instance
        else:
            try:
                self._execution_id = state['ExecutionId']
                self._plan = plan_class(self._loader, input_dict=state['Plan'])
            except Exception:
                message = 'Cannot load pass manager state from dict'
                logger.fatal(message)
                raise AwsReaperException(message)

    def export_to_dict(self):
        result = {
            'ExecutionId': self._execution_id,
            'Plan': self._plan.export()
        }
        return result

