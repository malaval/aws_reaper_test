from aws_reaper.common.base_service_loader import BaseServiceLoader


class ServiceLoader(BaseServiceLoader):
    """
    Load the service modules and implement methods to make it easier to access.

    """

    def describe(self, service, resource_type):
        """
        Args:
            service (str): Name of the service.
            resource_type (str): Name of the resource type.

        Returns:
            function: Return the describe function

        """
        return self.get_service(service).get_resource_type(resource_type)['Describe']

    def delete(self, service, resource_type):
        """
        Args:
            service (str): Name of the service.
            resource_type (str): Name of the resource type.

        Returns:
            function: Return the delete function

        """
        return self.get_service(service).get_resource_type(resource_type)['Delete']

    def max_wait(self, service, resource_type):
        """
        Args:
            service (str): Name of the service.
            resource_type (str): Name of the resource type.

        Returns:
            int: Maximum number of seconds to wait for resources of that resource type to be deleted

        """
        return self.get_service(service).get_resource_type(resource_type)['MaxWaitUntilDeleted']

    def list_iam_actions(self):
        """
        Return the list of IAM actions that you should allow and deny to prevent users from
        creating resources that the reaper script cannot delete.

        Returns:
            dict: Dictionary structured as follows::

                {
                    'Allow' (list): list of actions to whitelist.
                    'Deny' (list): list of actions to blacklist.
                }

        """
        allowed_actions = []
        denied_actions = []
        for service in self.list_services():
            denied_actions += self.get_service(service).get_denied_iam_actions().keys()
            for allowed_iam_service in self.get_service(service).get_allowed_iam_services():
                # Add service:* to allowed_actions unless any actions of that service is denied
                if not '%s:*' % allowed_iam_service in denied_actions:
                    allowed_actions.append('%s:*' % allowed_iam_service)
            allowed_actions += self.get_service(service).get_allowed_iam_services()
        return {
            'Allowed': sorted(allowed_actions),
            'Denied': sorted(denied_actions)
        }

    def list_denied_iam_actions_reason(self):
        """
        Return the list of IAM actions that you deny with an explanation for each action.

        Returns:
            dict: Dictionary structured as follows::

                {
                    'Denied IAM action': Reason
                }

        """
        result = {}
        for service in self.list_services():
            for key, value in self.get_service(service).get_denied_iam_actions().items():
                result[key] = value
        return result

    def get_friendly_name(self, service, resource_type=None):
        if resource_type is None:
            return self.get_service(service).get_friendly_name()
        else:
            return self.get_service(service).get_resource_type(resource_type)['FriendlyName']
