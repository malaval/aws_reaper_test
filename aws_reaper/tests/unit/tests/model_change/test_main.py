import json
import unittest
import os
import shutil
from os import path

from aws_reaper.tests.model_change.main import ModelChangeTest
from aws_reaper.common.exceptions import AwsReaperException


class TestModelChangeTest(unittest.TestCase):
    _tmp_dirname = path.join(path.dirname(path.abspath(__file__)), 'tmp_main', '')

    @classmethod
    def setUpClass(cls):
        """
        Create a temporary tmp folder and a parameters JSON document, and instantiate a new
        ModelChangeTest object.

        """
        # Create a tmp folder
        if not os.path.exists(cls._tmp_dirname):
            os.makedirs(cls._tmp_dirname)
        # Create a parameters JSON document
        parameters = {
            'cloudfront': {
                'IamUrls': [
                    'https://docs.aws.amazon.com/IAM/latest/UserGuide/list_amazoncloudfront.html'
                ],
                'IgnoredVerbs': [
                    'Get*',
                    'List*',
                    'Tag*',
                    'Untag*'
                ]
            },
            'ec2': {
                'IamUrls': [
                    'https://docs.aws.amazon.com/IAM/latest/UserGuide/list_amazonec2.html'
                ],
                'IgnoredVerbs': [
                    'Describe*'
                ]
            },
            'dummyservice': {}
        }
        parameters_filename = path.join(cls._tmp_dirname, 'parameters.json')
        with open(parameters_filename, 'w') as f:
            json.dump(parameters, f, indent=4)
        # Instantiate a ModelChangeTest object
        cls._test = ModelChangeTest(
            parameters_filename=parameters_filename,
            snapshot_dirname=cls._tmp_dirname
        )

    @classmethod
    def tearDownClass(cls):
        """Delete the tmp folder"""
        if os.path.exists(cls._tmp_dirname):
            shutil.rmtree(cls._tmp_dirname)

    def test_snapshot_service_model(self):
        self._test.snapshot_service_model('ec2')
        filename = self._test._snapshot_filename_pattern % 'ec2'
        with open(filename, 'r') as f:
            ec2_snapshot = json.load(f)
        self.assertIn('RunInstances', ec2_snapshot['IamActions'])
        os.remove(filename)

    def test_snapshot_service_model_exception(self):
        # Should raise an AwsReaperException because rds is not in the parameters file
        self.assertRaises(AwsReaperException, self._test.snapshot_service_model, 'rds')

    def test_snapshot_all(self):
        self._test.snapshot_all()
        for service in ('ec2', 'cloudfront'):
            filename = self._test._snapshot_filename_pattern % service
            with open(filename, 'r') as f:
                snapshot = json.load(f)
            self.assertGreater(len(snapshot['IamActions']), 0)
            os.remove(filename)

    def test_diff_service_model(self):
        # Should return an empty list of IAM actions added
        self._test.snapshot_service_model('ec2')
        model_diff = self._test.diff_service_model('ec2')
        self.assertEqual(len(model_diff['IamActions']['Added']), 0)

    def test_diff_service_model_exception1(self):
        # Should raise an AwsReaperException because dummyservice does not exist in boto3
        self.assertRaises(AwsReaperException, self._test.diff_service_model, 'dummyservice')

    def test_diff_service_model_exception2(self):
        # Should raise an AwsReaperException because there is no snapshot for rds
        self.assertRaises(AwsReaperException, self._test.diff_service_model, 'rds')

    def test_diff_all(self):
        self._test.snapshot_all()
        model_diff = self._test.diff_all()
        self.assertIn('dummyservice', model_diff['Services']['Removed'])
        self.assertIn('rds', model_diff['Services']['Added'])


if __name__ == '__main__':
    unittest.main()
