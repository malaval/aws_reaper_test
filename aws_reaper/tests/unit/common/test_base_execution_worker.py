import time
import unittest

from aws_reaper.service_loader import ServiceLoader
from aws_reaper.common.base_execution_worker import BaseExecutionWorker
from aws_reaper.execution_plan import ExecutionPlan


class TestBaseExecutionWorker(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.loader = ServiceLoader()

    def test_run(self):
        # Run workers to process an execution plan and check that all steps have been completed
        plan = ExecutionPlan(self.loader)
        worker = BaseExecutionWorker(self.loader, 2)
        plan.populate_plan(included_patterns=['*:*:*:*'], excluded_patterns=[])

        def no_sleep_function(a, b, c):
            time.sleep(0)

        plan_completed = worker._run(plan, no_sleep_function)
        self.assertEqual(0, plan.count_remaining_steps())
        self.assertTrue(plan_completed is True)

    def test_run_2(self):
        # Interrupt workers with a timeout
        plan = ExecutionPlan(self.loader)
        worker = BaseExecutionWorker(self.loader, 2)
        plan.populate_plan(included_patterns=['*:*:*:*'], excluded_patterns=[])

        def sleep_function(a, b, c):
            time.sleep(0.5)

        init_count = plan.count_remaining_steps()
        plan_completed = worker._run(plan, sleep_function, timeout=1)
        self.assertGreater(init_count, plan.count_remaining_steps())
        self.assertGreater(plan.count_remaining_steps(), 0)
        self.assertTrue(plan_completed is False)

    def test_attempt(self):

        def valid_function():
            return int(0/1)

        worker = BaseExecutionWorker(self.loader, 2)
        result = worker._attempt(valid_function, '{}')
        self.assertEqual(result, 0)

    def test_attempt_exception(self):

        def invalid_function():
            return int(0/0)

        worker = BaseExecutionWorker(self.loader, 2)
        self.assertRaises(Exception, worker._attempt, invalid_function, '{}')


if __name__ == '__main__':
    unittest.main()
