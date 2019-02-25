import logging

import botocore.session

from aws_reaper.common.exceptions import AwsReaperException

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class BotoInputParser:
    """
    botocore describes the accepted inputs for an operation in a botocore.model.Shape object.
    A Shape object usually reference other Shape objects to fully describe the input shape,
    i.e. the accepted inputs.

    For example, the operation ec2:DeleteSnapshot has the following input_shape::

        <StructureShape(DeleteSnapshotRequest)>
            SnapshotId: <StringShape(String)>
            DryRun: <Shape(Boolean)>

    This class provides methods to generate a dict from a Shape object, and to compare
    generated dicts to find inputs that were added or removed between two versions.

    """

    def __init__(self):
        self._session = botocore.session.get_session()

    def _iterate_shape_element(self, shape_element, current_depth=1, max_depth=5):
        """
        Iterate over a botocore.model.Shape object to generate the dict.

        Args:
            shape_element (botocore.model.Shape): Shape object to transform into a dict
            current_depth (int): Current depth level. Starts with 1 and is incremented at each
                iteration of _iterate_shape_element
            max_depth (int): Maximum recursion depth

        Returns:
            dict: dict generated from shape_element

        """
        # Stop recursion when max_depth is reached to prevent an infinite loop
        if current_depth > max_depth:
            return shape_element.type_name
        # If the current element if a structure, it contains an attribute ``members`` that is a
        # list of tuples (name, Shape element). We iterate over the child Shape elements
        if shape_element.type_name == 'structure':
            return {
                i[0]: self._iterate_shape_element(i[1], current_depth + 1)
                for i in shape_element.members.items()
            }
        # If the current element if a list, it contains an attribute ``member`` that is a Shape
        # on which we iterate
        elif shape_element.type_name == 'list':
            return {
                '_list': self._iterate_shape_element(shape_element.member, current_depth + 1)
            }
        # If the current element if a map, it contains an attribute ``key`` and an attribute
        # ``value`` that are Shape elements on which we iterate
        elif shape_element.type_name == 'map':
            return {
                '_key': self._iterate_shape_element(shape_element.key, current_depth + 1),
                '_value': self._iterate_shape_element(shape_element.value, current_depth + 1)
            }
        else:
            # If the current element has an attribute ``enum`` that is not empty, then iterate on
            # each item in ``item``
            if hasattr(shape_element, 'enum') and len(shape_element.enum) > 0:
                return {
                    '_enum': {str(i): shape_element.type_name for i in shape_element.enum}
                }
            else:
                return shape_element.type_name

    def _get_dict_from_input_shape(self, input_shape):
        """
        Return a dict generated from input_shape, a botocore.model.Shape object returned by
        ``get_operation_model(operation)``
        
        Args:
            input_shape (botocore.model.Shape): object that defined the accepted inputs for an
                operation

        Returns:
            dict: input_shape transformed into a dict

        Example:
            The dict returned for the operation ec2:CreateTags is::

                {
                    "DryRun": "boolean",
                    "Resources": {
                        "_list": "string"
                    },
                    "Tags": {
                        "_list": {
                            "Value": "string",
                            "Key": "string"
                        }
                    }
                }

            The dict returned for the operation acm:UpdateCertificateOptions is::

                {
                    "CertificateArn": "string",
                    "Options": {
                        "CertificateTransparencyLoggingPreference": {
                            "_enum": {
                                "DISABLED": "string",
                                "ENABLED": "string"
                            }
                        }
                    }
                }

        """
        # Return an empty dict if the operation does not accept any input
        if input_shape is None:
            return {}
        return self._iterate_shape_element(input_shape)

    def _serialize_dict(self, input_dict, prefix=''):
        """
        Transform a dict into an array of strings to make it easier to identify attributes that
        added or removed.

        Args:
            input_dict (dict): dict to serialize
            prefix (str): Used for recursion

        Return
            list: List of strings

        Example:
            ``{'aaa': {'bbb': '111', 'ccc': '222'}}`` is serialized into ``['aaa/bbb/111',
            'aaa/ccc/222']``

        """
        response = []
        for k, v in input_dict.items():
            if type(v) == dict:
                response += self._serialize_dict(v, '%s%s/' % (prefix, k))
            else:
                response += ['%s%s/%s' % (prefix, k, v)]
        return response

    def get_operation_inputs(self, service, operation):
        """
        Returns a dict that describes the accepted inputs for a given API operation.

        Args:
            service (str): Name of the service (e.g. ec2)
            operation (str): Name of the operation (e.g. RunInstances)

        Returns:
            dict: Description of the accepted inputs

        Raises:
            AwsReaperException: If an error occurs when parsing the botocore Shape model

        """
        try:
            shape = self._session.get_service_model(service).operation_model(operation).input_shape
            return self._get_dict_from_input_shape(shape)
        except Exception:
            message = 'Cannot parse the botocore model for %s:%s' % (service, operation)
            logger.debug(message)
            raise AwsReaperException(message)

    def compare_inputs(self, old_dict, new_dict):
        """
        Serialize the dict that describe the accepted inputs and compare to returned arrays to
        find attributes that were added or removed.

        Args:
            old_dict (dict): dict returned by get_operation_model
            new_dict (dict): dict returned by get_operation_model

        Returns:
            dict::

                {
                    'Added': list of strings,
                    'Removed': list of strings
                }

        """
        old_dict_serialized = self._serialize_dict(old_dict)
        new_dict_serialized = self._serialize_dict(new_dict)
        return {
            'Added': [i for i in new_dict_serialized if i not in old_dict_serialized],
            'Removed': [i for i in old_dict_serialized if i not in new_dict_serialized]
        }
