from aws_reaper.tests.create_resources.service import *

service = Service()


def create(session, step):
    pass


service.add_resource_type(
    resource_type='instance',
    create=create,
    create_before=[
        'ec2:volume',
        'iam:role'
    ]
)


service.add_resource_type(
    resource_type='volume',
    create=create
)