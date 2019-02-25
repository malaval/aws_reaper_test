# Reviewed on October 22

import unittest

from aws_reaper.tests.model_change.aws_doc_parser import AwsDocParser
from aws_reaper.common.exceptions import AwsReaperException


class TestAWSDocParser(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls._html_parser = AwsDocParser()

    def test_list_iam_actions_1(self):
        # EC2 should return a list that contains RunInstances and CreateVolume
        doc_url = 'https://docs.aws.amazon.com/IAM/latest/UserGuide/list_amazonec2.html'
        actions = self._html_parser.list_iam_actions(doc_url)
        self.assertIn('RunInstances', actions)
        self.assertIn('CreateVolume', actions)

    def test_list_iam_actions_2(self):
        # RDS should return a list that contains CreateDBInstance
        doc_url = 'https://docs.aws.amazon.com/IAM/latest/UserGuide/list_amazonrds.html'
        actions = self._html_parser.list_iam_actions(doc_url)
        self.assertIn('CreateDBInstance', actions)

    def test_list_iam_actions_exception(self):
        # Raise an exception if the page does not exist
        doc_url = 'http://wrongdomain.com/404.html'
        self.assertRaises(AwsReaperException, self._html_parser.list_iam_actions, doc_url)


if __name__ == '__main__':
    unittest.main()
