from aws_reaper.service import *

service = Service('AWS Certificate Manager')
service.add_allowed_iam_service('acm')


def describe(client, step, **kwargs):
    """List of certificates managed by ACM"""
    return simple_describe(
        client, 'list_certificates',
        "[i['CertificateArn'] for i in data['CertificateSummaryList']]"
    )


def delete(client, id_to_delete, step, **kwargs):
    """Delete a certificate managed by ACM"""
    try:
        client.delete_certificate(CertificateArn=id_to_delete)
        return False
    except client.exceptions.ResourceNotFoundException:
        return False


service.add_resource_type(
    resource_type='certificate',
    friendly_name='Certificate',
    describe=describe,
    delete=delete
)
