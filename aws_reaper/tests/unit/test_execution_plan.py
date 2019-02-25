import unittest

from aws_reaper.execution_plan import ExecutionPlan
from aws_reaper.service_loader import ServiceLoader


class TestExecutionPlan(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.loader = ServiceLoader('aws_reaper.tests.unit.test_services')

    def test_populate_plan(self):
        plan = ExecutionPlan(self.loader)
        included = ['*:*:*:*']
        excluded = []
        plan.populate_plan(included_patterns=included, excluded_patterns=excluded)
        self.assertTrue(plan.count_remaining_steps() > 0)

    def test_populate_plan_2(self):
        # Exclude all possible resources
        plan = ExecutionPlan(self.loader)
        included = ['*:*:*:*']
        excluded = ['*:*:*:*']
        plan.populate_plan(included_patterns=included, excluded_patterns=excluded)
        self.assertTrue(plan.count_remaining_steps() == 0)

    def test_get_next_step(self):
        plan = ExecutionPlan(self.loader)
        included = ['*:*:*:*']
        excluded = []
        plan.populate_plan(included_patterns=included, excluded_patterns=excluded)
        step_key, step = plan.get_next_step()
        self.assertTrue(step_key is not None and step_key != 'wait')
        step_key2, step2 = plan.get_next_step()
        self.assertTrue(step_key2 is not None and step_key2 != 'wait' and step_key != step_key2)


if __name__ == '__main__':
    unittest.main()
