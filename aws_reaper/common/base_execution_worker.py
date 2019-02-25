import logging
import random
import threading
import time

import boto3

from aws_reaper.config import Config

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class BaseExecutionWorker:
    """
    Base class that implements common attributes and methods for the ExecutionWorker classes in
    aws_reaper.execution_worker and aws_reaper.tests.create_resources.execution_worker that creates
    concurrent threads to execute a plan.

    """

    def __init__(self, loader, nb_workers, **credentials):
        """
        Initialize a new BaseExecutionWorker object.

        Args:
            loader (:obj:`ServiceLoader`): ServiceLoader object
            nb_workers (int): Number of concurrent threads to create
            **credentials: AWS credentials passed to boto3

        """
        self._loader = loader
        self._nb_workers = nb_workers
        self._credentials = credentials
        self._lock = threading.Lock()
        # We use a threading Lock object to prevent multiple threads to update the execution plan
        # at the same time
        self._event_next_step = threading.Event()
        # We use a threading Event to inform threads that are waiting for a step to process
        # that a step has just completed so they can retry obtaining a step.
        self._event_timeout = threading.Event()
        # We use a threading Event to inform threads a timeout has occurred. The threads stops as
        # soon as the event is set to True.

    def _attempt(self, func, msg_pattern, *args, **kwargs):
        """
        Execute a function `func`. If the function fails, we retry ``NB_RETRIES`` times and we raise
        the returning exception if the last retry fails. Between each attempt, we wait for a
        random period of time that increases proportionately with the number of retries.

        Args:
            func (func): Pointer to the function to execute.
            msg_pattern (str): Format string used to log traceback when an attempt fails. The
                string must contain one positional argument that is filled by the attempt number.
            *args: Argument list passed to ``func``.
            *kwargs: Keyword arguments passed to ``func``.

        Returns:
            obj: Return the output of the function ``func``

        """

        i = 0
        wait_seconds = random.uniform(1.0, 2.0)
        while True:
            i += 1
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.debug(msg_pattern.format(i), exc_info=True)
                if i >= Config.NB_RETRIES:
                    raise e
                self._event_timeout.wait(wait_seconds * i)
                # Exit if _event_timeout is triggered
                if self._event_timeout.is_set():
                    raise e

    def _run(self, plan, f, timeout=None, **kwargs):
        """
        Create new threads to process an execution plan.

        Args:
            plan (:obj:`ExecutionPlan`): Execution plan to process
            f (function): Function that is called to process a step
            timeout (int): The threads will stop if the execution time exceeds timeout seconds.
                Default is ``None`` to disable timeout.
            **kwargs: Keyword arguments that are passed to f

        Returns:
            bool: Return True if all the steps in the plan were completed

        """
        self._event_next_step.clear()
        self._event_timeout.clear()

        def worker_func():
            session = boto3.session.Session(**self._credentials)
            thread_name = threading.current_thread().name
            step = None
            while True:
                # Stop if a timeout has occurred
                if self._event_timeout.is_set():
                    break
                # Acquire the lock, notify the threads that are waiting for a step to
                # complete, obtain a step to process then release the lock.
                self._lock.acquire()
                if step is not None:
                    step.status = 'Completed'
                    self._event_next_step.set()
                    self._event_next_step.clear()
                step_key, step = plan.get_next_step()
                self._lock.release()
                # If there is no more step to process then terminate the thread.
                if step_key == 'end':
                    logger.debug('[%s] No more plan key' % thread_name)
                    return
                # If step_key is ``wait`` then retry when another step completes
                if step_key == 'wait':
                    logger.debug('[%s] Waiting for dependencies to complete' % thread_name)
                    self._event_next_step.wait()
                    continue
                logger.debug('[%s] [%s] Processing new plan key' % (thread_name, step_key))
                f(thread_name, session, step, **kwargs)

        try:
            # Start CONCURRENT_WORKERS threads
            threads = [threading.Thread(name='worker%s' % (i+1), target=worker_func)
                       for i in range(self._nb_workers)]
            logger.debug('Starting %s concurrent threads' % self._nb_workers)
            [t.start() for t in threads]

            # Wait for all threads to complete, or if ``timeout`` is set, when the threads have been
            # running for ``timeout`` seconds.
            if timeout is not None:
                end_time = time.time() + timeout
                for t in threads:
                    join_arg = end_time - time.time()
                    t.join(join_arg)
            else:
                # KeyboardInterrupt is implemented only when the timeout is not set, because it
                # corresponds to an interactive usage
                while len([t for t in threads if t.is_alive()]) > 0:
                    [t.join(1) for t in threads]

            # If there are still threads alive, set the event _event_timeout and wait for threads to
            # stop properly
            if len([t for t in threads if t.is_alive()]) > 0:
                logger.debug('Sending timeout event to threads')
                self._event_timeout.set()
                # Set the event ``_event_next_step`` so the threads that are waiting for a step to
                # complete can also stop
                self._event_next_step.set()
                for t in threads:
                    t.join(None)

            # Steps with a step ongoing are reset to NoStarted because count_remaining_steps returns
            # the number of NotStarted steps
            plan.reset_ongoing_status()
            return plan.count_remaining_steps() == 0

        # KeyboardInterrupt are not detected when the process waits for threads to join.
        # That is why we use an infinite loop and join with 1 second
        except KeyboardInterrupt:
            self._event_timeout.set()
            self._event_next_step.set()
            logger.warning('Execution interrupted')
            raise KeyboardInterrupt
