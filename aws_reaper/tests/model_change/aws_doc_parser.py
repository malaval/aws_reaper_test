import re
import logging
import sys

from aws_reaper.common.exceptions import AwsReaperException

# Fix Python 2
_ver = sys.version_info
is_py2 = (_ver[0] == 2)
if is_py2:
    # noinspection PyUnresolvedReferences,PyUnresolvedReferences
    from urllib2 import urlopen
    # noinspection PyUnresolvedReferences,PyUnresolvedReferences
    from HTMLParser import HTMLParser
else:
    from urllib.request import urlopen
    from html.parser import HTMLParser

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class AwsDocParser(HTMLParser):
    """
    Parse the AWS documentation to retrieve a list of supported IAM actions. Example of page:
    https://docs.aws.amazon.com/IAM/latest/UserGuide/list_amazonec2.html

    The HTML code is processed as follows:

    1. Isolate the code that is between the H2 tag that contains "actions" and the next H2 tag
    2. In this section, identify the TD tags that contains a A tag with an "id" attribute
    3. The first word in these TD tags refers to an IAM action

    """

    def error(self, message):
        pass

    def __init__(self, create_new=True):
        """
        Initialize a new AWSDocParser object.

        Args:
            create_new (bool): Set to True to create a new object, False to reinitialize object
                variables before calling ``list_iam_actions``.

        """
        if create_new:
            HTMLParser.__init__(self)
        self.actions = []
        self.last_tag_was_h2 = False
        self.in_actions_h2_tag = False
        self.in_td_tag = False
        self.is_action_td_tag = False

    def list_iam_actions(self, url):
        """
        This function initializes the object variables used when HTMLParser parses the AWS
        documentation page and returns an array of IAM actions.

        Args:
            url (str): URL of the AWS documentation to parse

        Returns:
            list: List of IAM actions (string)

        Raises:
            AwsReaperException: If an error occurs when loading or parsing the AWS documentation

        """
        try:
            html_content = str(urlopen(url).read())
            self.__init__(create_new=False)
            self.feed(html_content)
            return self.actions
        except Exception as e:
            message = 'Cannot parse the IAM documentation: %s' % str(e)
            logger.debug(message)
            raise AwsReaperException(message)

    def handle_starttag(self, tag, attrs):
        if tag == 'h2':
            self.last_tag_was_h2 = True
        if self.in_actions_h2_tag:
            if tag == 'td':
                self.in_td_tag = True
            if tag == 'a' and self.in_td_tag:
                for (key, value) in attrs:
                    if key == 'id':
                        self.is_action_td_tag = True

    def handle_endtag(self, tag):
        if tag == 'td':
            self.in_td_tag = False
            self.is_action_td_tag = False

    def handle_data(self, data):
        if self.last_tag_was_h2:
            self.in_actions_h2_tag = 'actions' in data.lower()
            self.last_tag_was_h2 = False
        if self.is_action_td_tag:
            if len(data) > 0:
                # Return only the first word of the tag data that is at least 3-char long
                action = re.search('\w{3,99}', data)
                if action is not None:
                    self.actions.append(action.group(0))
