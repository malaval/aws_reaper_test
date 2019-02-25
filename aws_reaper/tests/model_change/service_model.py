# Reviewed on October 22

import copy
import re
import logging

import botocore.session

from aws_reaper.tests.model_change.aws_doc_parser import AwsDocParser
from aws_reaper.tests.model_change.boto_input_parser import BotoInputParser
from aws_reaper.common.exceptions import AwsReaperException

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

aws_doc_parser = AwsDocParser()
boto_input_parser = BotoInputParser()
session = botocore.session.get_session()


class ServiceModel:
    """
    Describe the model of a service, i.e. the IAM actions supported by that service and the
    accepted inputs.

    Attributes:
        iam_actions (list): List of IAM actions that are supported by this service
        operation_inputs (dict): List of accepted inputs for all the operations with
            ``operation_inputs[operation]`` a dict returned by BotoInputParser that describes the
            accepted inputs for ``operation``.

    """

    @staticmethod
    def _is_verb_ignored(verb, ignored_verbs):
        """
        Return True if a verb (IAM action or operation) action [or operation] matches one of the
        ignored verb patterns.

        Args:
            verb (str)
            ignored_verbs (list): List of verb patterns that are ignored. You can
                only include wildcard characters in your patterns (e.g. Describe*)

        Example:
            If ``ignored_verbs`` equals ``['Describe*', 'List*']`` then
            ``_is_verb_ignored('RunInstances', ignored_actions)`` returns ``False`` but
            ``_is_verb_ignored('DescribeInstances', ignored_actions)`` returns ``True``

        Returns:
            bool: True if the verb should be ignored

        """
        for ignored_verb in ignored_verbs:
            regex = ('^' + re.escape(ignored_verb) + '$').replace('\*', '.*')
            if re.match(regex, verb) is not None:
                return True
        # Return False if verb matches with no ignored verb patterns
        return False

    def __init__(self):
        self.iam_actions = []
        self.operation_inputs = {}

    def load(self, service, iam_urls, ignored_actions):
        """
        Retrieve the IAM actions and accepted inputs for each of the API operations.

        Args:
            service (str): Name of the service
            iam_urls (list): List of URLs of the AWS IAM documentation to parse for this service.
                There is usually one URL per service, but some services might have more than one
                like API Gateway
            ignored_actions (list): List of verb patterns that are ignored. You can
                only include wildcard characters in your patterns (e.g. Describe*)

        Raises:
            AwsReaperException: If an error occurs

        """
        try:
            # Retrieve the supported IAM actions for this service unless that action is ignored
            self.iam_actions = []
            for iam_url in iam_urls:
                for action in aws_doc_parser.list_iam_actions(iam_url):
                    if not self._is_verb_ignored(action, ignored_actions):
                        self.iam_actions.append(action)
            # Retrieve the accepted inputs of all the operations for this service unless that
            # operation is ignored
            self.operation_inputs = {}
            for operation in session.get_service_model(service).operation_names:
                if not self._is_verb_ignored(operation, ignored_actions):
                    inputs = boto_input_parser.get_operation_inputs(service, operation)
                    self.operation_inputs[operation] = inputs
        except AwsReaperException:
            message = 'Failed to load service model'
            logger.debug(message)
            raise AwsReaperException(message)
        except Exception as e:
            message = 'Failed to load service model: %s' % str(e)
            logger.debug(message)
            raise AwsReaperException(message)

    def load_from_dict(self, input_dict):
        """
        Load the IAM actions and accepted inputs from a dict.

        Args:
            input_dict (dict):

        Raises:
            AwsReaperException: If an error occurs

        """
        try:
            # Create a copy to avoid unexpected references
            copy_dict = copy.deepcopy(input_dict)
            self.iam_actions = copy_dict['IamActions']
            self.operation_inputs = copy_dict['OperationInputs']
        except Exception as e:
            message = 'Failed to load service model from dict: %s' % str(e)
            logger.debug(message)
            raise AwsReaperException(message)

    def export_to_dict(self):
        """
        Return a dict that describes the ServiceModel instance.

        Returns:
            dict:

        """
        return {
            'IamActions': self.iam_actions,
            'OperationInputs': self.operation_inputs
        }


class ServiceModelDiff:
    """
    Compare two ServiceModel objects and determine changes.

    Attributes:
        iam_actions_added (list): List of IAM actions that were added
        iam_actions_removed (list): List of IAM actions that were added
        operations_added (list): List of operations that were added
        operations_added (list): List of operations that were added
        operation_inputs_added (list): List of operation inputs that were added
        operation_inputs_added (list): List of operation inputs that were removed

    """

    def __init__(self, old_model, new_model):
        """
        Initialize a new ServiceModelDiff object.

        Args:
            old_model (:obj:`ServiceModel`): Old service model to compare
            new_model (:obj:`ServiceModel`): New service model to compare

        """
        self.iam_actions_added = []
        self.iam_actions_removed = []
        self.operations_added = []
        self.operations_removed = []
        self.operation_inputs_added = []
        self.operation_inputs_removed = []

        # Find IAM actions that were added or removed
        new_actions = new_model.iam_actions
        old_actions = old_model.iam_actions
        self.iam_actions_added = sorted([i for i in new_actions if i not in old_actions])
        self.iam_actions_removed = sorted([i for i in old_actions if i not in new_actions])

        # Find operations that were added or removed
        new_ops = new_model.operation_inputs.keys()
        old_ops = old_model.operation_inputs.keys()
        self.operations_added = sorted([i for i in new_ops if i not in old_ops])
        self.operations_removed = sorted([i for i in old_ops if i not in new_ops])

        # Find operation inputs that were added or removed
        for operation in [i for i in new_ops if i in old_ops]:
            new_inputs = new_model.operation_inputs[operation]
            old_inputs = old_model.operation_inputs[operation]
            diff_inputs = boto_input_parser.compare_inputs(old_inputs, new_inputs)
            for i in diff_inputs['Added']:
                self.operation_inputs_added.append('%s:%s' % (operation, i))
            for i in diff_inputs['Removed']:
                self.operation_inputs_removed.append('%s:%s' % (operation, i))

    def export_to_dict(self):
        return {
            'IamActions': {
                'Added': self.iam_actions_added,
                'Removed': self.iam_actions_removed
            },
            'Operations': {
                'Added': self.operations_added,
                'Removed': self.operations_removed
            },
            'OperationInputs': {
                'Added': self.operation_inputs_added,
                'Removed': self.operation_inputs_removed
            }
        }
