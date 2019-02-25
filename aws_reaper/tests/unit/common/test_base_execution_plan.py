import unittest

from aws_reaper.service_loader import ServiceLoader
from aws_reaper.common.base_execution_plan import BaseExecutionPlan
from aws_reaper.execution_plan import ExecutionPlanStep
from aws_reaper.common.exceptions import AwsReaperException


class TestBaseExecutionPlan(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.loader = ServiceLoader('aws_reaper.tests.unit.test_services')

    def test_is_global_service(self):
        # Check that _is_global_service returns Route 53 and Cost Explorer as global services,
        # and EC2 as regional service
        plan = BaseExecutionPlan(self.loader, ExecutionPlanStep)
        self.assertTrue(plan._is_global_service('route53'))
        self.assertTrue(plan._is_global_service('ce'))
        self.assertFalse(plan._is_global_service('ec2'))

    def test_get_regions_for_service(self):
        # Check that get_regions_for_service returns eu-west-1 as a region supported by EC2,
        # us-east-1 for IAM and, not eu-west-3 for SES (currently not supported in Paris)
        plan = BaseExecutionPlan(self.loader, ExecutionPlanStep)
        self.assertIn('eu-west-1', plan.get_regions_for_service('ec2'))
        self.assertIn('us-east-1', plan.get_regions_for_service('iam'))
        self.assertNotIn('eu-west-3', plan.get_regions_for_service('ses'))

    def test_get_regions_for_service_2(self):
        # Check that eu-west-3 is listed as a region supported by SES if we override the botocore
        # regions
        plan = BaseExecutionPlan(self.loader, ExecutionPlanStep, override_botocore_regions=True)
        self.assertIn('eu-west-3', plan.get_regions_for_service('ses'))

    def test_add_step(self):
        # Add a step using add_step that checks that this step exists
        plan = BaseExecutionPlan(self.loader, ExecutionPlanStep)
        step = plan.add_step('ec2', 'us-east-1', 'instance')
        self.assertIn('ec2:us-east-1:instance', plan.get_steps().keys())
        self.assertIn('ec2:us-east-1:volume', step.dependencies)

    def test_step_exists(self):
        plan = BaseExecutionPlan(self.loader, ExecutionPlanStep)
        plan.add_step('ec2', 'us-east-1', 'instance')
        self.assertTrue(plan.step_exists('ec2', 'us-east-1', 'instance'))

    def test_add_step_exception_1(self):
        # Check that add_step returns an exception is the service passed is not defined in the
        # service modules
        plan = BaseExecutionPlan(self.loader, ExecutionPlanStep)
        self.assertRaises(AwsReaperException, plan.add_step, 'dummy', 'us-east-1', 'dummy')

    def test_export(self):
        plan = BaseExecutionPlan(self.loader, ExecutionPlanStep)
        plan.add_step('ec2', 'us-east-1', 'instance')
        plan_dict = plan.export()
        self.assertIn('ec2:us-east-1:instance', plan_dict.keys())

    def test_export_not_full(self):
        plan = BaseExecutionPlan(self.loader, ExecutionPlanStep)
        plan.add_step('ec2', 'us-east-1', 'instance')
        plan_export = plan.export(full=False)
        self.assertEqual(type(plan_export), list)

    def test_load_from_dict_exception_1(self):
        # Check that creating an execution plan from an invalid dict fails
        plan_dict = {
            'ec2:us-east-1:instance': {
                'Wrong': 'Input'
            }
        }
        self.assertRaises(
            AwsReaperException,
            BaseExecutionPlan, self.loader, ExecutionPlanStep, input_dict=plan_dict
        )

    def test_load_from_dict(self):
        plan_dict = {
            'ec2:us-east-1:instance': {
                'Status': 'NotStarted',
                'Service': 'ec2',
                'ResourceType': 'instance',
                'Region': 'us-east-1',
                'DeleteAfter': ['ec2:us-east-1:volume'],
                'StartTime': 0,
                'DescribeError': '',
                'ResourceIdPatternsToDelete': [],
                'ResourceIdPatternsToExclude': [],
                'ResourceIdsToDelete': [],
                'ResourceIdsDeleted': [],
                'ResourceIdsExcluded': [],
                'ResourceIdsFailedToDelete': {},
                'WaitForDeletionUntil': 0
            }
        }
        plan = BaseExecutionPlan(self.loader, ExecutionPlanStep, input_dict=plan_dict)
        self.assertIn('ec2:us-east-1:instance', plan.get_steps().keys())

    def test_reset_ongoing_status(self):
        plan = BaseExecutionPlan(self.loader, ExecutionPlanStep)
        step = plan.add_step('ec2', 'us-east-1', 'instance')
        step.status = 'Ongoing'
        plan.reset_ongoing_status()
        self.assertEqual(1, plan.count_remaining_steps())

    def test_count_remaining_steps(self):
        plan = BaseExecutionPlan(self.loader, ExecutionPlanStep)
        self.assertEqual(0, plan.count_remaining_steps())
        step = plan.add_step('ec2', 'us-east-1', 'instance')
        self.assertEqual(1, plan.count_remaining_steps())
        step.status = 'Completed'
        self.assertEqual(0, plan.count_remaining_steps())

    def test_copy(self):
        # Copy the execution plan, add a step to the copy, and check that the number of steps of
        # the copy is different than the number of steps of the original execution plan
        plan = BaseExecutionPlan(self.loader, ExecutionPlanStep)
        plan.add_step('ec2', 'us-east-1', 'instance')
        plan2 = plan.copy()
        plan2.add_step('iam', 'us-east-1', 'role')
        self.assertNotEqual(plan.count_remaining_steps(), plan2.count_remaining_steps())


if __name__ == '__main__':
    unittest.main()
