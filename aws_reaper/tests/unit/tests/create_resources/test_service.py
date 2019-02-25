import unittest

from aws_reaper.tests.create_resources.service import Service
from aws_reaper.common.exceptions import AwsReaperException


class TestService(unittest.TestCase):

    @staticmethod
    def create():
        pass

    @classmethod
    def setUpClass(cls):
        cls.service = Service()

    def test_add_resource_type(self):
        self.service.add_resource_type(
            resource_type='test_resource_type',
            create=self.create,
            create_before=['test_service:test_resource_type']
        )
        self.assertIn('test_resource_type', self.service.list_resource_types())
        self.assertIn('Create', self.service.get_resource_type('test_resource_type').keys())

    def test_add_resource_type_exception_1(self):
        self.assertRaises(
            AwsReaperException, self.service.add_resource_type,
            resource_type='',  # Empty string
            create=self.create,
            create_before=['test_service:test_resource_type']
        )


if __name__ == '__main__':
    unittest.main()
