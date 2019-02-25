from aws_reaper.tests.create_resources.service import *

service = Service()


def create(session, step, **kwargs):
    client = session.client(step.service, region_name=step.region)
    domain_name = 'awsreaper.example.com'
    # Check whether the certificate already exists
    try:
        arn = [
            i['CertificateArn']
            for i in client.list_certificates()['CertificateSummaryList']
            if i['DomainName'] == domain_name
        ][0]
    # If not, create a new certificate
    except IndexError:
        arn = client.request_certificate(DomainName=domain_name)['CertificateArn']
    step.resources_created['CertificateArn'] = arn
    return False


service.add_resource_type(
    resource_type='certificate',
    create=create
)
