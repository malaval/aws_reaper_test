import logging
import time

from aws_reaper.config import Config
from aws_reaper.common.base_execution_worker import BaseExecutionWorker

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class ExecutionWorker(BaseExecutionWorker):
    """
    Inherit from BaseExecutionWorker to create threads that process each step of an execution plan
    to create resources.

    """

    def _f_create(self, thread_name, session, step, **kwargs):
        """
        Function that is called by threads to create resources for a given step.

        Args:
            thread_name (str): Name of the thread for logging purposes
            session (:obj:`botocore._session.Session`): Botocore _session object
            step (:obj:`ExecutionPlanStep`): Object for the step to process
            **kwargs (): Keyword argument to pass to the describe function

        Returns:

        """
        # Create resources, and if needed wait for resources to be completely created.
        while True:
            start_time = time.time()

            # Stop the thread if a timeout has occurred.
            if self._event_timeout.is_set():
                return

            try:
                message = '[%s] [%s] Creating resources' % (thread_name, step.step_key)
                logger.debug(message)
                wait_for_creation = self._attempt(
                    self._loader.create(step.service, step.resource_type),
                    '[%s] [%s] Attempt {} failed' % (thread_name, step.step_key),
                    session, step, **kwargs
                )

                # If we must wait for the resource to be completely deleted
                if wait_for_creation:
                    message = '[%s] [%s] Waiting for resources to create' \
                              % (thread_name, step.step_key)
                    logger.info(message)
                else:
                    message = '[%s] [%s] Created resources' % (thread_name, step.step_key)
                    logger.info(message)
                    return

            # If the current step failed to create
            except Exception as e:
                step.create_error = str(e)
                message = '[%s] [%s] Failed to create: %s' % (thread_name, step.step_key, e)
                logger.error(message, exc_info=True)
                return

            # Exit the loop if we wait for resources to create for more than MAX_WAIT_UNTIL_DELETED
            # minutes.
            if time.time() - step.start_time > Config.MAX_WAIT_UNTIL_DELETED:
                step.create_error = "Timeout"
                message = '[%s] [%s] Failed to create: Timeout' % (thread_name, step.step_key)
                logger.error(message)
                return

            # Wait and check again if resources are completely deleted
            delta_time = Config.WAIT_BETWEEN_RETRIES - (time.time() - start_time)
            if delta_time > 0.0:
                self._event_timeout.wait(delta_time)

    def run_create(self, plan, timeout=None, **kwargs):
        """
        Create threads to create resources in an AWS account.

        Args:
            plan (:obj:`ExecutionPlan`): Execution plan to process
            timeout (int): The threads will stop if the execution time exceeds timeout seconds.
                Default is ``None`` to disable timeout.
            **kwargs (): Keyword arguments to pass to the describe function

        """
        return self._run(plan, self._f_create, timeout, **kwargs)
