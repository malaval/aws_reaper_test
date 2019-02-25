import unittest
from inspect import isfunction

from aws_reaper.tests.create_resources.service_loader import ServiceLoader


class TestServiceLoader(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.loader = ServiceLoader('aws_reaper.tests.unit.tests.create_resources.test_services')

    def test_create(self):
        self.assertTrue(isfunction(self.loader.create('ec2', 'instance')))

    def test_get_dependencies(self):
        self.assertIn('ec2:volume', self.loader.get_dependencies('ec2', 'instance'))

