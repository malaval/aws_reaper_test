import logging

from aws_reaper.common.base_execution_manager import BaseExecutionManager
from aws_reaper.execution_plan import ExecutionPlan
from aws_reaper.config import Config
from aws_reaper.common.exceptions import AwsReaperException

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class CheckExecutionManager(BaseExecutionManager):

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


class CleanExecutionManager(BaseExecutionManager):

    def __init__(
            self, loader, plan_class=ExecutionPlan, init_plan=None, state=None,
            min_passes=Config.MIN_PASSES, max_passes=Config.MIN_PASSES
    ):
        """

        Args:
            loader ():
            plan_class ():
            init_plan ():
            state ():
            min_passes ():
            max_passes ():
        """
        BaseExecutionManager.__init__(self, loader, plan_class, init_plan, state)
        self._min_passes = min_passes
        self._max_passes = max_passes
        if state is None:
            self._nb_passes = 1
            self._previous_plan = None
            logger.info('New execution %s' % self._execution_id)
        else:
            try:
                self._nb_passes = state['NbPasses']
                if 'PreviousPlan' in state:
                    previous_plan = ExecutionPlan(self._loader, input_dict=state['PreviousPlan'])
                    self._previous_plan = previous_plan
                else:
                    self._previous_plan = None
                logger.info('Resuming execution %s' % self._execution_id)
            except Exception:
                message = 'Cannot load pass manager state from dict'
                logger.fatal(message)
                raise AwsReaperException(message)

    def _create_new_pass(self):
        """
        Create a copy of the current execution it, so it can be used to run a new pass.

        """
        new_plan = self._plan.copy()
        self._previous_plan = self._plan
        self._plan = new_plan
        self._nb_passes += 1

    @staticmethod
    def _get_deleted(plan):
        """
        Return the list of resource IDs that were successfully deleted in the execution plan

        Args:
            plan (obj): Execution plan

        Returns:
            list (str)

        Args:
            plan ():

        Returns:

        """
        result = []
        for step_key, step in plan.get_steps().items():
            result += ['%s:%s' % (step_key, i) for i in step.resource_ids_deleted]
        return result

    @staticmethod
    def _get_failed_to_delete(plan):
        """
        Return the list of resource IDs that failed to delete in the execution plan

        Args:
            plan (obj): Execution plan

        Returns:
            list (str)

        """
        result = []
        for step_key, step in plan.get_steps().items():
            result += ['%s:%s' % (step_key, i) for i in step.resource_ids_failed_to_delete.keys()]
        return result

    def get_next_plan(self):
        """
        Returns the execution plan to execute for the current pass, or ``None`` if there is no more
        pass to run. A new pass is needed if the minimum number of passes is not reached,
        or if new resources were deleted or failed to delete in the previous pass.

        Returns:
            :obj:`ExecutionPlan` or None

        """
        # If the current plan is completed
        if self._plan.count_remaining_steps() == 0:
            # Return None if the maximum number of passes is reached
            if self._nb_passes == self._max_passes:
                return None
            # If the minimum number of passes is not yet reach, no need to evaluate whether you
            # need to run a new pass
            elif self._nb_passes < self._min_passes:
                self._create_new_pass()
            else:
                # If min_passes is 1 but some resources failed to delete, create a new pass
                current_failed = CleanExecutionManager._get_failed_to_delete(self._plan)
                if self._previous_plan is None:
                    if len(current_failed) > 0:
                        self._create_new_pass()
                    else:
                        return None
                # Otherwise, create a new pass if the current pass has resources that were
                # deleted or failed to delete that were not in the previous plan
                else:
                    current_deleted = CleanExecutionManager._get_deleted(self._plan)
                    previous_deleted = CleanExecutionManager._get_deleted(self._previous_plan)
                    previous_failed = CleanExecutionManager._get_failed_to_delete(
                        self._previous_plan
                    )
                    new_deleted = [i for i in current_deleted if i not in previous_deleted]
                    new_failed = [i for i in current_failed if i not in previous_failed]
                    if len(new_deleted) == 0 and len(new_failed) == 0:
                        return None
                    else:
                        self._create_new_pass()

        logger.info(
            '[PASS %s] %s steps remaining' %
            (self._nb_passes, self._plan.count_remaining_steps())
        )
        return self._plan

    def export_to_dict(self):
        """
        Return a dict that represents the current state of the execution manager. Override the
        function defined by BaseExecutionManager by adding the attributs ``NbPasses`` and
        ``PreviousPlan``.

        Returns:
            dict

        """
        result = BaseExecutionManager.export_to_dict(self)
        result['NbPasses'] = self._nb_passes
        if self._previous_plan is not None:
            result['PreviousPlan'] = self._previous_plan.export()
        return result
