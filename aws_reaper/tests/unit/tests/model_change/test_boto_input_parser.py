import unittest

from aws_reaper.tests.model_change.boto_input_parser import BotoInputParser
from aws_reaper.common.exceptions import AwsReaperException


class TestBotoInputParser(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.parser = BotoInputParser()

    def test_get_operation_inputs_1(self):
        # ec2:RunInstances should have an attribute ImageId
        result = self.parser.get_operation_inputs('ec2', 'RunInstances')
        self.assertTrue('ImageId' in result)

    def test_get_operation_inputs_2(self):
        # ec2:RunInstances should have an attribute BlockDeviceMappings that is a list
        result = self.parser.get_operation_inputs('ec2', 'RunInstances')
        self.assertTrue('_list' in result['BlockDeviceMappings'])

    def test_get_operation_inputs_3(self):
        # ec2:RunInstances should have an attribute InstanceType that is an enum
        result = self.parser.get_operation_inputs('ec2', 'RunInstances')
        self.assertTrue('_enum' in result['InstanceType'])

    def test_get_operation_inputs_exception(self):
        self.assertRaises(
            AwsReaperException,
            self.parser.get_operation_inputs,
            'ec2', 'DummyAction'
        )
        self.assertRaises(
            AwsReaperException,
            self.parser.get_operation_inputs,
            'dummyservice', 'DummyAction'
        )

    def test_compare_inputs(self):
        # If inputs1 and inputs2 are the same, check that compare_inputs(inputs1, inputs2) returns 
        # a dict with no added or removed inputs
        inputs1 = self.parser.get_operation_inputs('ec2', 'RunInstances')
        inputs2 = self.parser.get_operation_inputs('ec2', 'RunInstances')
        diff_inputs = self.parser.compare_inputs(inputs1, inputs2)
        expected = {'Added': [], 'Removed': []}
        self.assertDictEqual(expected, diff_inputs)
        # Remove an attribute from inputs2 and check that compare_inputs returns that
        # removed attribute in Removed
        del(inputs2['ImageId'])
        diff_inputs = self.parser.compare_inputs(inputs1, inputs2)
        expected = {'Added': [], 'Removed': ['ImageId/string']}
        self.assertDictEqual(expected, diff_inputs)
        diff_inputs = self.parser.compare_inputs(inputs2, inputs1)
        expected = {'Added': ['ImageId/string'], 'Removed': []}
        self.assertDictEqual(expected, diff_inputs)


if __name__ == '__main__':
    unittest.main()
