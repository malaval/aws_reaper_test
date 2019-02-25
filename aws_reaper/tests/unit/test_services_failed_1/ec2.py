from aws_reaper.service import *

service = Service()
service.add_allowed_iam_service('ec2')
service.add_denied_iam_action('ec2', '*Purchase*', 'Reason')
service.add_allowed_iam_service('dummy')
service.add_denied_iam_action('dummy', '*', 'Reason')
service.add_service_role_name('test.amazonaws.com')


def describe(client, step):
    pass


def delete(client, id_to_delete, step):
    pass


service.add_resource_type(
    resource_type='instance',
    friendly_name='EC2 instance',
    describe=describe,
    delete=delete,
    delete_after=['ec2:volume'],
    max_wait_until_deleted=100
)

service.add_resource_type(
    resource_type='volume',
    friendly_name='EBS volume',
    describe=describe,
    delete_after=['ec2:instance'],
    delete=delete
)
