import logging

from aws_reaper.common.base_execution_manager import BaseExecutionManager
from aws_reaper.tests.create_resources.execution_plan import ExecutionPlan

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class CreateExecutionManager(BaseExecutionManager):

    def __init__(self, loader, plan_class=ExecutionPlan, init_plan=None, state=None):
        """
        Create an execution manager either by passing an initial execution plan, or a dict that
        represents the state returned by a previous execution manager.

        Args:
            loader (:obj:`ServiceLoader`): ServiceLoader object
            plan_class (obj): Class for execution plan. No need to change the default value.
            init_plan (obj): Initial execution plan
            state (dict): Provide a dict to preload the execution manager from a previous state.
                Do not provide a value for ``init_plan`` if you pass a value to ``state``

        """
        BaseExecutionManager.__init__(self, loader, plan_class, init_plan, state)
        if state is None:
            logger.info('New execution %s' % self._execution_id)
        else:
            logger.info('Resuming execution %s' % self._execution_id)

    def get_plan(self):
        """
        Returns:
            obj:`ExecutionPlan`: Return the execution plan

        """
        logger.info('%s steps remaining' % self._plan.count_remaining_steps())
        return self._plan
