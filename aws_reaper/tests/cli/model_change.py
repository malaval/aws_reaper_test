# Reviewed on October 22

import argparse
import random

import aws_reaper.tests.cli.common
from aws_reaper.tests.model_change.main import ModelChangeTest
from aws_reaper.common.exceptions import AwsReaperException

# Fix Python 2.x.
try:
    # noinspection PyShadowingBuiltins,PyUnresolvedReferences
    input = raw_input
except NameError:
    pass


def main():
    parser = argparse.ArgumentParser(
        description='Find changes made to the IAM actions and API operations that a service '
                    'supports'
    )
    parser.add_argument(
        'action',
        choices=['diff', 'snapshot'],
        help='Action: "diff" to compare the current service model with the snapshot, '
             '"snapshot" to create a snapshot of the service model.')
    parser.add_argument('service', help='Name of the service or "all"')
    parser.add_argument('-d', '--debug', action='store_true')
    parser.add_argument(
        '--override', action='store_true',
        help='Replace a snapshot if it already exists'
    )
    parser.add_argument(
        '--parameters_filename', required=False, default=None,
        help='Location of the JSON parameters file'
    )
    parser.add_argument(
        '--snapshot_dirname', required=False, default=None,
        help='Folder where snapshot reside'
    )
    args = parser.parse_args()

    logger = aws_reaper.tests.cli.common.get_cli_logger(debug=args.debug)

    try:
        model_change_test = ModelChangeTest(args.snapshot_dirname, args.parameters_filename)

        if args.action == 'diff':
            messages = []

            if args.service == 'all':
                result = model_change_test.diff_all()
                for service in result['Services']['Added']:
                    messages.append('%s - Service added' % service)
                for service in result['Services']['Removed']:
                    messages.append('%s - Service removed' % service)
                for service, content in result['Services']['Existing'].items():
                    for item in content['IamActions']['Added']:
                        messages.append('%s - IAM action added: %s' % (service, item))
                    for item in content['IamActions']['Removed']:
                        messages.append('%s - IAM action removed: %s' % (service, item))
                    for item in content['Operations']['Added']:
                        messages.append('%s - Operation added: %s' % (service, item))
                    for item in content['Operations']['Removed']:
                        messages.append('%s - Operation removed: %s' % (service, item))
                    for item in content['OperationInputs']['Added']:
                        messages.append('%s - Input added: %s' % (service, item))
                    for item in content['OperationInputs']['Removed']:
                        messages.append('%s - Input removed: %s' % (service, item))

            else:
                result = model_change_test.diff_service_model(args.service)
                for item in result['IamActions']['Added']:
                    messages.append('IAM action added: %s' % item)
                for item in result['IamActions']['Removed']:
                    messages.append('IAM action removed: %s' % item)
                for item in result['Operations']['Added']:
                    messages.append('Operation added: %s' % item)
                for item in result['Operations']['Removed']:
                    messages.append('Operation removed: %s' % item)
                for item in result['OperationInputs']['Added']:
                    messages.append('Input added: %s' % item)
                for item in result['OperationInputs']['Removed']:
                    messages.append('Input removed: %s' % item)

            # Sort and print the messages
            if len(messages) > 0:
                for message in sorted(messages):
                    logger.info(message)
            else:
                logger.info('No change')

        elif args.action == 'snapshot':
            # Ask the user to enter a given value to prevent unexpected override of snapshots
            if args.override:
                expected = '%s %s' % (args.service, random.randint(1, 100))
                submitted = input('Enter "%s" to confirm override: ' % expected)
                if expected != submitted:
                    logger.warning('Incorrect input')
                    return
            if args.service == 'all':
                model_change_test.snapshot_all(args.override)
            else:
                model_change_test.snapshot_service_model(args.service, args.override)

    except AwsReaperException:
        pass
    except Exception as e:
        logger.fatal(str(e), exc_info=True)


if __name__ == '__main__':
    main()
