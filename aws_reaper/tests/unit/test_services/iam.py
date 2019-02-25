from aws_reaper.service import *

service = Service()
service.add_allowed_iam_service('iam')


def describe(client, step):
    pass


def delete(client, id_to_delete, step):
    pass


service.add_resource_type(
    resource_type='role',
    friendly_name='IAM role',
    describe=describe,
    delete=delete,
    max_wait_until_deleted=100
)
