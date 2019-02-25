import unittest

from aws_reaper.common.base_service_loader import BaseServiceLoader
from aws_reaper.common.exceptions import AwsReaperException


class TestBaseServiceLoader(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.loader = BaseServiceLoader('aws_reaper.tests.unit.test_services')

    def test_list_services(self):
        self.assertIn('ec2', self.loader.list_services())

    def test_get_service(self):
        self.loader.get_service('ec2')

    def test_list_resource_types(self):
        self.assertIn('instance', self.loader.list_resource_types('ec2'))

    def test_list_all_resource_types(self):
        self.assertIn(('ec2', 'instance'), self.loader.list_all_resource_types())

    def test_get_dependencies(self):
        self.assertIn('ec2:volume', self.loader.get_dependencies('ec2', 'instance'))

    def test_exception_1(self):
        # Test fails because the service modules contain an infinite loop
        self.assertRaises(
            AwsReaperException,
            BaseServiceLoader, 'aws_reaper.tests.unit.test_services_failed_1'
        )

    def test_exception_2(self):
        # Test fails because the service modules contain an invalid dependency
        self.assertRaises(
            AwsReaperException,
            BaseServiceLoader, 'aws_reaper.tests.unit.test_services_failed_2'
        )

    def test_resource_type_exists(self):
        self.assertTrue(self.loader.resource_type_exists('ec2', 'instance'))

    def test_resource_type_exists_2(self):
        self.assertFalse(self.loader.resource_type_exists('ec2', 'dummy'))
        self.assertFalse(self.loader.resource_type_exists('dummy', 'dummy'))


if __name__ == '__main__':
    unittest.main()
