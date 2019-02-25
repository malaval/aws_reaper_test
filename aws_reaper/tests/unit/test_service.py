import unittest

from aws_reaper.service import Service
from aws_reaper.common.exceptions import AwsReaperException


class TestService(unittest.TestCase):

    @staticmethod
    def describe():
        pass

    @staticmethod
    def delete():
        pass

    @classmethod
    def setUpClass(cls):
        cls.service = Service()

    def test_add_resource_type(self):
        self.service.add_resource_type(
            resource_type='test_resource_type',
            friendly_name='Test Resource Type',
            describe=self.describe,
            delete=self.delete,
            delete_after=['test_service:test_resource_type'],
            max_wait_until_deleted=10
        )
        self.assertIn('test_resource_type', self.service.list_resource_types())
        self.assertIn('FriendlyName', self.service.get_resource_type('test_resource_type').keys())

    def test_add_resource_type_exception_1(self):
        self.assertRaises(
            AwsReaperException, self.service.add_resource_type,
            resource_type='',  # Empty string
            friendly_name='Test Resource Type',
            describe=self.describe,
            delete=self.delete,
            delete_after=['test_service:test_resource_type']
        )

    def test_add_resource_type_exception_2(self):
        self.assertRaises(
            AwsReaperException, self.service.add_resource_type,
            resource_type='test_resource_type',
            friendly_name='Test Resource Type',
            describe='string',  # Not a function
            delete='string',  # Not a function
            delete_after=['test_service:test_resource_type']
        )


if __name__ == '__main__':
    unittest.main()
