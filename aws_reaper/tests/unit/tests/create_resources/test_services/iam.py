from aws_reaper.tests.create_resources.service import *

service = Service()


def create(session, step):
    pass


service.add_resource_type(
    resource_type='role',
    create=create
)