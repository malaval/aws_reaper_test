import logging
import re
import time

from aws_reaper.config import Config
from aws_reaper.common.base_execution_worker import BaseExecutionWorker

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


def match_regex(value, patterns):
    """
    Args:
        value (str): Value to check. Example: prefix_instance
        patterns (list): List of regex patterns that may contain a wildcard. Example: prefix*

    Returns:
        bool: Return True if value matches at least one pattern

    """
    match = False
    for pattern in patterns:
        pattern_regex = '^' + re.escape(pattern) + '$'
        pattern_regex = pattern_regex.replace('\*', '.*')
        if re.match(pattern_regex, value) is not None:
            match = True
            break
    return match


class ExecutionWorker(BaseExecutionWorker):
    """
    Inherit from BaseExecutionWorker to create threads that process each step of an execution plan
    to find and delete resources in an AWS account.

    """

    def _f_describe(self, thread_name, session, step, client=None, **kwargs):
        """
        Function that is called by threads to describe resources for a given step.

        Args:
            thread_name (str): Name of the thread for logging purposes
            session (:obj:`botocore._session.Session`): Botocore _session object
            step (:obj:`ExecutionPlanStep`): Object for the step to process
            client (:obj:`botocore.client`): When ``_f_describe_and_delete`` calls
                ``_f_describe``, it passes the boto client to avoid creating another client.
            **kwargs (): Keyword argument to pass to the describe function

        """
        if client is None:
            client = session.client(step.service, region_name=step.region)

        # Retrieve the resource identifiers for the step
        try:
            ids_existing = self._attempt(
                self._loader.describe(step.service, step.resource_type),
                '[%s] [%s] Attempt {} failed' % (thread_name, step.step_key),
                client, step, **kwargs
            )
        except Exception as e:
            error_message = '[%s] %s' % (type(e).__name__, str(e))
            step.describe_error = error_message
            message = '[%s] [%s] Describe failed: %s' % (thread_name, step.step_key, e)
            logger.error(message, exc_info=True)
            return

        # For each resource identifier
        for id_existing in ids_existing:
            # Check whether the resource identifier is explicitly excluded
            included = match_regex(id_existing, step.resource_id_patterns_to_delete)
            # Check whether the resource identifier is explicitly included
            excluded = match_regex(id_existing, step.resource_id_patterns_to_exclude)
            if included and not excluded:
                if id_existing not in step.resource_ids_to_delete:
                    step.resource_ids_to_delete.append(id_existing)
            else:
                if id_existing not in step.resource_ids_excluded:
                    step.resource_ids_excluded.append(id_existing)

        message = '[%s] [%s] %s resources to delete, %s excluded' \
                  % (thread_name, step.step_key, len(step.resource_ids_to_delete),
                     len(step.resource_ids_excluded))
        logger.debug(message)

    def _f_describe_and_delete(self, thread_name, session, step, **kwargs):
        """
        Function that is called by threads to describe and delete resources for a given step.

        Args:
            thread_name (str): Name of the thread for logging purposes
            session (:obj:`botocore._session.Session`): Botocore _session object
            step (:obj:`ExecutionPlanStep`): Object for the step to process
            **kwargs (): Keyword argument to pass to the describe function

        Returns:

        """
        client = session.client(step.service, region_name=step.region)
        self._f_describe(thread_name, session, step, client, **kwargs)

        # Stop the thread if a timeout has occurred.
        if self._event_timeout.is_set():
            return

        # Delete each existing resources that are included, and if needed wait for resources to
        # be completely deleted.
        while True:
            start_iteration = time.time()

            # Copy the list of resources to delete because the original list is modified within the
            # iteration
            ids_to_delete = list(step.resource_ids_to_delete)
            for id_to_delete in ids_to_delete:

                # Stop the thread if a timeout has occurred.
                if self._event_timeout.is_set():
                    return

                try:
                    message = '[%s] [%s] Deleting %s' % (thread_name, step.step_key, id_to_delete)
                    logger.debug(message)
                    wait_for_deletion = self._attempt(
                        self._loader.delete(step.service, step.resource_type),
                        '[%s] [%s] Attempt {} failed' % (thread_name, step.step_key),
                        client, id_to_delete, step, **kwargs
                    )

                    # If we must wait for the resource to be completely deleted
                    if wait_for_deletion:
                        message = '[%s] [%s] Waiting for %s to delete' \
                                  % (thread_name, step.step_key, id_to_delete)
                        logger.info(message)
                    else:
                        step.resource_ids_to_delete.remove(id_to_delete)
                        step.resource_ids_deleted.append(id_to_delete)
                        message = '[%s] [%s] Deleted %s' \
                                  % (thread_name, step.step_key, id_to_delete)
                        logger.info(message)

                # If the current resource failed to delete
                except Exception as e:
                    step.resource_ids_to_delete.remove(id_to_delete)
                    error_message = '[%s] %s' % (type(e).__name__, str(e))
                    step.resource_ids_failed_to_delete[id_to_delete] = error_message
                    message = '[%s] [%s] Failed to delete %s: %s' \
                              % (thread_name, step.step_key, id_to_delete, e)
                    logger.error(message, exc_info=True)

            # Exit the loop if there is no more resource to delete
            if len(step.resource_ids_to_delete) == 0:
                return

            # Exit the loop if we wait for resources to delete for too long
            delta_time = time.time() - step.start_time
            if delta_time > self._loader.max_wait(step.service, step.resource_type):
                break

            # Wait and check again if resources are completely deleted. Delta time is the number
            # of seconds between iterations, minus the time already spent in the current iteration
            delta_time = Config.WAIT_BETWEEN_RETRIES - (time.time() - start_iteration)
            if delta_time > 0.0:
                self._event_timeout.wait(delta_time)

        # If we interrupt the step because it was running for too long, then mark the remaining
        # resources as failed
        ids_to_delete = list(step.resource_ids_to_delete)
        for id_to_delete in ids_to_delete:
            step.resource_ids_to_delete.remove(id_to_delete)
            step.resource_ids_failed_to_delete[id_to_delete] = "Timeout"
            message = '[%s] [%s] Failed to delete %s: Timeout' \
                      % (thread_name, step.step_key, id_to_delete)
            logger.error(message)

    def run_describe(self, plan, timeout=None, **kwargs):
        """
        Create threads to describe resources in an AWS account.

        Args:
            plan (:obj:`ExecutionPlan`): Execution plan to process
            timeout (int): The threads will stop if the execution time exceeds timeout seconds.
                Default is ``None`` to disable timeout.
            **kwargs (): Keyword arguments to pass to the describe function

        Returns:
            bool: Return True if all the steps in the plan were completed

        """
        return self._run(plan, self._f_describe, timeout, **kwargs)

    def run_describe_and_delete(self, plan, timeout=None, **kwargs):
        """
        Create threads to delete resources in an AWS account.

        Args:
            plan (:obj:`ExecutionPlan`): Execution plan to process
            timeout (int): The threads will stop if the execution time exceeds timeout
            seconds.
                Default is ``None`` to disable timeout.
            **kwargs (): Keyword arguments to pass to the describe function

        Returns:
            bool: Return True if all the steps in the plan were completed

        """
        return self._run(plan, self._f_describe_and_delete, timeout, **kwargs)
