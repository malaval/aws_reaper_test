import unittest

from aws_reaper.common.base_execution_manager import BaseExecutionManager
from aws_reaper.execution_plan import ExecutionPlan
from aws_reaper.service_loader import ServiceLoader
from aws_reaper.common.exceptions import AwsReaperException


class TestBaseExecutionManager(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.loader = ServiceLoader()

    def test_create_from_init_plan(self):
        # Create a new execution manager from an initial execution plan
        plan = ExecutionPlan(self.loader)
        manager = BaseExecutionManager(self.loader, ExecutionPlan, init_plan=plan)
        manager_dict = manager.export_to_dict()
        self.assertIn('Plan', manager_dict)

    def test_create_from_state(self):
        # Create a new execution manager from a plan, export the state to a dict,
        # create another execution manager from that state and compare the execution ID
        plan = ExecutionPlan(self.loader)
        manager = BaseExecutionManager(self.loader, ExecutionPlan, init_plan=plan)
        manager_dict = manager.export_to_dict()
        manager2 = BaseExecutionManager(self.loader, ExecutionPlan, state=manager_dict)
        manager2_dict = manager2.export_to_dict()
        self.assertEqual(manager_dict['ExecutionId'], manager2_dict['ExecutionId'])

    def test_create_exception(self):
        # Provide an invalid dict and check that creating an execution manager from that dict fails
        dummy_state = {
            'DummyAttribute': 'DummyValue'
        }
        self.assertRaises(
            AwsReaperException, BaseExecutionManager, self.loader, ExecutionPlan,
            state=dummy_state
        )


if __name__ == '__main__':
    unittest.main()
