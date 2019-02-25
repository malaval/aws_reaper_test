# Reviewed on October 22

import json
import logging
from os import path

import botocore.session

from aws_reaper.tests.model_change.service_model import ServiceModel
from aws_reaper.tests.model_change.service_model import ServiceModelDiff
from aws_reaper.common.exceptions import AwsReaperException

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

session = botocore.session.get_session()

SNAPSHOT_FOLDER = 'snapshots'
PARAMETERS_FILENAME = 'parameters.json'


class ModelChangeTest:
    """
    Find changes made to the IAM actions and API operations that a service supports, and to the
    inputs that are accepted by an API operation.

    This class stores snapshots of service models as JSON documents, and compares them with
    the latest service models to identify changes. When a change is detected, an update of the
    AWS reaper script might be required.

    """

    def __init__(self, snapshot_dirname=None, parameters_filename=None):
        """
        Initialize a new ModelChangeTest object.

        Args:
            snapshot_dirname (str): Folder that stores the service model snapshots as JSON
                documents. Default value is ``./snapshots/``
            parameters_filename (str): Location of the parameters.json. Default value is
                ``./parameters.json``. The structure of the JSON document should be as following::

                    {
                        "service_name": {
                            "IamUrls" (optional): list of URLs to the AWS IAM documentation
                                that lists the IAM actions, resources and conditions for that
                                service. Default is an empty list
                            "IgnoredVerbs" (optional): list of case sensitive verb patterns. Each
                                pattern that may  contain one or more wildcard characters. Any
                                IAM action or API operation that matches this pattern is
                                ignored. Default is an empty list
                        },
                        ...
                    }

        Raises:
            AwsReaperException: If the JSON parameters file cannot be read.

        """
        this_dirname = path.dirname(path.abspath(__file__))  # Current folder
        self._snapshot_filename_pattern = None  # Snapshot filename pattern with %s as the service
        self._parameters_filename = None  # Location of the JSON parameters file
        self._parameters = None  # Content of the JSON parameters file

        # Set the value of self._snapshot_filename_pattern based on parameters_filename
        if snapshot_dirname is None:
            self._snapshot_filename_pattern = path.join(this_dirname, SNAPSHOT_FOLDER, '%s.json')
        else:
            self._snapshot_filename_pattern = path.join(snapshot_dirname, '%s.json')
        logger.debug('Snapshot filename pattern = %s' % self._snapshot_filename_pattern)

        # Set self._parameters_filename to the default value if no value was passed to the
        # constructor
        self._parameters_filename = parameters_filename
        if self._parameters_filename is None:
            self._parameters_filename = path.join(this_dirname, PARAMETERS_FILENAME)
        logger.debug('Parameters filename = %s' % self._parameters_filename)

        # Load the parameters file in self._parameters
        try:
            with open(self._parameters_filename, 'r') as f:
                self._parameters = json.load(f)
        except Exception:
            message = 'Failed to open %s' % self._parameters_filename
            logger.fatal(message)
            raise AwsReaperException(message)

    def _get_service_model(self, service):
        """
        Returns the current model for a given service.

        Args:
            service (str): Name of the service

        Returns:
            :obj:`ServiceModel`

        Raises:
            AwsReaperException: If the service cannot be found in the JSON parameters file

        """
        try:
            parameters_service = self._parameters[service]
        except KeyError:
            message = 'No service %s found in the parameters file' % service
            logger.debug(message)
            raise AwsReaperException(message)
        # Set iam_urls to an empty list if no IamUrls attribute is provided in the JSON
        # parameters file for that service
        try:
            iam_urls = parameters_service['IamUrls']
        except KeyError:
            iam_urls = []
        # Set ignored_verbs to an empty list if no IgnoredVerbs attribute is provided in the JSON
        # parameters file for that service
        try:
            ignored_verbs = parameters_service['IgnoredVerbs']
        except KeyError:
            ignored_verbs = []
        model = ServiceModel()
        model.load(service, iam_urls, ignored_verbs)
        return model

    def _load_service_model_from_snapshot(self, service):
        """
        Loads the snapshot for a given service and returns the service model.

        Args:
            service (str): Name of the service

        Returns:
            :obj:`ServiceModel`

        Raises:
            AwsReaperException: If the service cannot be found in the JSON parameters file

        """
        snapshot_filename = self._snapshot_filename_pattern % service
        try:
            with open(snapshot_filename, 'r') as f:
                snapshot = json.load(f)
            model = ServiceModel()
            model.load_from_dict(snapshot)
            return model
        except Exception:
            message = 'No valid snapshot for %s at %s' % (service, snapshot_filename)
            logger.debug(message)
            raise AwsReaperException(message)

    def _snapshot_service_model(self, service, override_snapshots=False):
        """
        Writes a snapshot for a given service.

        Args:
            service (str): Name of the service
            override_snapshots (boolean): Replace the snapshot if it already exists

        Raises:
            AwsReaperException: If an error occurs

        """
        filename = self._snapshot_filename_pattern % service
        # Exit if the file already exists and override_snapshots is set to False
        if path.isfile(filename) and not override_snapshots:
            logger.info('Snapshot for %s already exists' % service)
            return
        try:
            model = self._get_service_model(service)
            snapshot = model.export_to_dict()
            with open(filename, 'w') as f:
                json.dump(snapshot, f, sort_keys=True, indent=4)
            logger.info('Created snapshot for %s' % service)
        except Exception:
            message = 'Cannot create snapshot for %s at %s' % (service, filename)
            logger.debug(message)
            raise AwsReaperException(message)

    def _diff_service_model(self, service):
        """
        Compare the current model of a given service with its snapshot.

        Args:
            service (str): Name of the service

        Returns:
            dict: see diff_service_model

        Raises:
            AwsReaperException: If an error occurs

        """
        try:
            new = self._get_service_model(service)
            old = self._load_service_model_from_snapshot(service)
            model_diff = ServiceModelDiff(old, new)
            return model_diff.export_to_dict()
        except AwsReaperException:
            message = 'Cannot find differences for %s' % service
            logger.debug(message)
            raise AwsReaperException(message)

    def snapshot_service_model(self, service, override_snapshots=False):
        """
        Write a snapshot for a given service.

        Args:
            service (str): Name of the service
            override_snapshots (boolean): Replace the snapshot if it already exists

        Raises:
            AwsReaperException: If an error occurs

        """
        try:
            self._snapshot_service_model(service, override_snapshots)
        except AwsReaperException:
            message = 'Cannot write snapshot for %s' % service
            logger.fatal(message)
            raise AwsReaperException(message)

    def snapshot_all(self, override_snapshots=False):
        """
        Write a snapshot for all of the services supported by botocore.

        Args:
            override_snapshots (bool): Replace a snapshot if it already exists

        """
        services = session.get_available_services()
        for service in services:
            try:
                self._snapshot_service_model(service, override_snapshots)
            except AwsReaperException:
                message = 'Cannot create snapshot for %s' % service
                logger.debug(message)

    def diff_service_model(self, service):
        """
        Compare the current model of a given service with its snapshot.

        Args:
            service (str): Name of the service

        Returns:
            dict: dict with the following structure::

                {
                    'IamActions': {
                        'Added': list of IAM actions added in the form of ``action``,
                        'Removed': list of IAM actions removed in the form of ``action``
                    },
                    'Operations': {
                        'Added': list of API operations added in the form of ``operation``,
                        'Removed': list of API operations removed in the form of ``operation``
                    },
                    'OperationInputs': {
                        'Added': list of inputs added in the form of ``operation:input``,
                        'Removed': list of inputs removed in the form of ``operation:input``
                    }
                }

        Raises:
            AwsReaperException: If an error occurs

        """
        try:
            return self._diff_service_model(service)
        except AwsReaperException:
            message = 'Cannot find differences for %s' % service
            logger.fatal(message)
            raise AwsReaperException(message)

    def diff_all(self):
        """
        Compare the current model of all of the services with their snapshot.

        Returns:
            dict: dict with the following structure::

                {
                    'Services': {
                        'Added': list of services added in the form of ``service``,
                        'Removed': list of services removed in the form of ``service``,
                        'Existing': {
                            'service_name': {
                                'IamActions': {
                                    'Added': list of IAM actions added,
                                    'Removed': list of IAM actions removed
                                },
                                'Operations': {
                                    'Added': list of API operations added,
                                    'Removed': list of API operations removed
                                },
                                'OperationInputs': {
                                    'Added': list of inputs added,
                                    'Removed': list of inputs removed
                                }
                            }
                        }
                    }
                }

        Raises:
            AwsReaperException: If an error occurs

        """
        result = {
            'Services': {
                'Added': [],
                'Removed': [],
                'Existing': {}
            }
        }
        try:
            # Identify services that were added or removed
            new = session.get_available_services()
            old = self._parameters.keys()
            result['Services']['Added'] = sorted([i for i in new if i not in old])
            result['Services']['Removed'] = sorted([i for i in old if i not in new])
            # Compare other services with the latest snapshots
            for service in [i for i in old if i in new]:
                logger.debug('Processing diff for %s' % service)
                model_diff = self._diff_service_model(service)
                result['Services']['Existing'][service] = model_diff
            return result
        except AwsReaperException:
            message = 'Cannot find differences'
            logger.fatal(message)
            raise AwsReaperException(message)
