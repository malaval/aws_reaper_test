import argparse
import os

import aws_reaper.tests.cli.common

from aws_reaper.service_loader import ServiceLoader as ReaperServiceLoader
from aws_reaper.tests.create_resources.service_loader import ServiceLoader as CreatorServiceLoader
from aws_reaper.common.exceptions import AwsReaperException

path = __file__.replace('aws_reaper/tests/cli/generate_doc.py', '')


def main():
    parser = argparse.ArgumentParser(description='Generate documentation for AWS Reaper')
    parser.add_argument('-d', '--debug', action='store_true')
    args = parser.parse_args()

    logger = aws_reaper.tests.cli.common.get_cli_logger(debug=args.debug)

    try:
        # Write the table header
        md_content = 'Service | Resource Type | What ``describe`` returns | What ``delete`` does ' \
                     '| *Creator* can create test resources\n'
        md_content += '---- | ---- | ---- | ---- | ----\n'

        # Populate the table for each supported resource type
        loader = ReaperServiceLoader()
        creator_loader = CreatorServiceLoader()
        for service in loader.list_services():
            s_friendly_name = loader.get_friendly_name(service)
            for resource_type in loader.list_resource_types(service):
                r_friendly_name = loader.get_friendly_name(service, resource_type)
                describe_note = loader.describe(service, resource_type).__doc__
                delete_note = loader.delete(service, resource_type).__doc__
                creator_exists_bool = creator_loader.resource_type_exists(service, resource_type)
                creator_exists_text = 'Yes' if creator_exists_bool else 'No'
                md_content += '%s (%s) | %s (%s) | %s | %s | %s\n' %\
                              (service, s_friendly_name, resource_type, r_friendly_name,
                               describe_note, delete_note, creator_exists_text)

        # Create output dir if it does not already exist
        pathname = path + 'doc/generated'
        os.makedirs(pathname, exist_ok=True)

        # Write the content to a file
        filename = pathname + '/resource_types.md'
        with open(filename, 'w') as f:
            f.writelines(md_content)

    except AwsReaperException:
        pass
    except Exception as e:
        logger.fatal(str(e), exc_info=True)


if __name__ == '__main__':
    main()
