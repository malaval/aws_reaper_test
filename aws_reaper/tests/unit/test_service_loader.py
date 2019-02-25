import unittest
from inspect import isfunction

from aws_reaper.service_loader import ServiceLoader


class TestServiceLoader(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.loader = ServiceLoader('aws_reaper.tests.unit.test_services')

    def test_describe(self):
        self.assertTrue(isfunction(self.loader.describe('ec2', 'instance')))

    def test_delete(self):
        self.assertTrue(isfunction(self.loader.delete('ec2', 'instance')))

    def test_get_dependencies(self):
        self.assertIn('ec2:volume', self.loader.get_dependencies('ec2', 'instance'))

    def test_max_wait(self):
        self.assertEqual(self.loader.max_wait('ec2', 'instance'), 100)

    def test_list_all_iam_actions(self):
        iam_actions = self.loader.list_iam_actions()
        self.assertIn('ec2:*', iam_actions['Allowed'])
        self.assertIn('ec2:*Purchase*', iam_actions['Denied'])
        self.assertNotIn('dummy:*', iam_actions['Allowed'])

    def test_list_denied_iam_actions_reason(self):
        denied_actions = self.loader.list_denied_iam_actions_reason()
        self.assertIn('ec2:*Purchase*', denied_actions.keys())
        self.assertEqual('Reason', denied_actions['ec2:*Purchase*'])
