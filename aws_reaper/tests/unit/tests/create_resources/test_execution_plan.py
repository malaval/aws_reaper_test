import unittest

from aws_reaper.tests.create_resources.service_loader import ServiceLoader
from aws_reaper.tests.create_resources.execution_plan import ExecutionPlan


class TestExecutionPlan(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.loader = ServiceLoader('aws_reaper.tests.unit.tests.create_resources.test_services')

    def test_populate_plan(self):
        plan = ExecutionPlan(self.loader)
        included = ['ec2:us-east-1:instance']
        plan.populate_plan(included_patterns=included)
        self.assertTrue(plan.count_remaining_steps() >= 2)

    def test_get_next_step(self):
        plan = ExecutionPlan(self.loader)
        included = ['*:*:*']
        plan.populate_plan(included_patterns=included)
        step_key, step = plan.get_next_step()
        self.assertTrue(step_key is not None and step_key != 'wait')
        step_key2, step2 = plan.get_next_step()
        self.assertTrue(step_key is not None and step_key2 != 'wait' and step_key != step_key2)


if __name__ == '__main__':
    unittest.main()
