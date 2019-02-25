import unittest

from aws_reaper.tests.model_change.service_model import ServiceModel
from aws_reaper.tests.model_change.service_model import ServiceModelDiff
from aws_reaper.common.exceptions import AwsReaperException


class TestServiceModel(unittest.TestCase):

    def test_load(self):
        iam_urls = ['https://docs.aws.amazon.com/fr_fr/IAM/latest/UserGuide/list_amazonec2.html']
        ignored_actions = ['Describe*']
        model = ServiceModel()
        model.load('ec2', iam_urls, ignored_actions)
        self.assertIn('RunInstances', model.iam_actions)
        self.assertNotIn('DescribeInstances', model.iam_actions)
        self.assertIn('RunInstances', model.operation_inputs.keys())
        self.assertIn('InstanceType', model.operation_inputs['RunInstances'].keys())

    def test_load_exception_1(self):
        iam_urls = ['https://docs.aws.amazon.com/fr_fr/IAM/latest/UserGuide/list_amazonec2.html']
        ignored_actions = ['Describe*']
        model = ServiceModel()
        self.assertRaises(
            AwsReaperException,
            model.load, 'dummyservice', iam_urls, ignored_actions
        )

    def test_load_exception_2(self):
        iam_urls = ['http://wrongdomain.com/404.html']
        ignored_actions = ['Describe*']
        model = ServiceModel()
        self.assertRaises(
            AwsReaperException,
            model.load, 'ec2', iam_urls, ignored_actions
        )

    def test_export_to_dict(self):
        model = ServiceModel()
        model.iam_actions = ['A', 'B']
        model.operation_inputs = {'A': {'InputA': 'string'}, 'B': {'InputB': 'string'}}
        model_dict = model.export_to_dict()
        self.assertIn('A', model_dict['IamActions'])
        self.assertNotIn('C', model_dict['IamActions'])
        self.assertIn('A', model_dict['OperationInputs'].keys())
        self.assertIn('InputA', model_dict['OperationInputs']['A'].keys())

    def test_load_from_dict(self):
        model_dict = {
            'IamActions': ['A', 'B'],
            'OperationInputs': {'A': {'InputA': 'string'}, 'B': {'InputB': 'string'}}
        }
        model = ServiceModel()
        model.load_from_dict(model_dict)
        self.assertIn('A', model.iam_actions)
        self.assertNotIn('C', model.iam_actions)
        self.assertIn('A', model.operation_inputs.keys())
        self.assertIn('InputA', model.operation_inputs['A'].keys())

    def test_load_from_dict_exception(self):
        model_dict = {
            'WrongInput': ['A', 'B'],
            'OperationInputs': {'A': {'InputA': 'string'}, 'B': {'InputB': 'string'}}
        }
        model = ServiceModel()
        self.assertRaises(
            AwsReaperException,
            model.load_from_dict, model_dict
        )


class TestServiceModelDiff(unittest.TestCase):

    def test_init(self):
        old_model = ServiceModel()
        old_model.iam_actions = ['A', 'B']
        old_model.operation_inputs = {'A': {'InputA': 'string'}, 'B': {'InputB': 'string'}}
        new_model = ServiceModel()
        new_model.iam_actions = ['A', 'C']
        new_model.operation_inputs = {'A': {'InputD': 'string'}, 'C': {'InputC': 'string'}}
        model_diff = ServiceModelDiff(old_model, new_model)
        self.assertTrue(len(model_diff.iam_actions_added) > 0)
        self.assertTrue(len(model_diff.iam_actions_removed) > 0)
        self.assertTrue(len(model_diff.operations_added) > 0)
        self.assertTrue(len(model_diff.operations_removed) > 0)
        self.assertTrue(len(model_diff.operation_inputs_added) > 0)
        self.assertTrue(len(model_diff.operation_inputs_removed) > 0)
        return model_diff

    def test_export_to_dict(self):
        model_diff = self.test_init()
        model_diff_dict = model_diff.export_to_dict()
        self.assertTrue(len(model_diff_dict['IamActions']['Added']) > 0)
        self.assertTrue(len(model_diff_dict['IamActions']['Removed']) > 0)
        self.assertTrue(len(model_diff_dict['Operations']['Added']) > 0)
        self.assertTrue(len(model_diff_dict['Operations']['Removed']) > 0)
        self.assertTrue(len(model_diff_dict['OperationInputs']['Added']) > 0)
        self.assertTrue(len(model_diff_dict['OperationInputs']['Removed']) > 0)


if __name__ == '__main__':
    unittest.main()
