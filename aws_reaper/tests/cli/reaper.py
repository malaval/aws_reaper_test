import argparse
import json
import random

import boto3

import aws_reaper.tests.cli.common
from aws_reaper.main import Reaper
from aws_reaper.common.exceptions import AwsReaperException

# Fix Python 2
try:
    # noinspection PyShadowingBuiltins,PyUnresolvedReferences
    input = raw_input
except NameError:
    pass


def main():
    parser = argparse.ArgumentParser(description='AWS Reaper')
    parser.add_argument('-d', '--debug', action='store_true')
    sub_parser = parser.add_subparsers(title='commands')

    parser_1 = sub_parser.add_parser(
        'list_resource_types',
        help='List the types of resources that the reaper script currently supports.'
    )
    parser_1.set_defaults(command='list_resource_types')

    # parser_2 = sub_parser.add_parser(
    #     'list_iam_actions',
    #     help='List the IAM actions that you should allow or deny to prevent users from '
    #          'creating resources that the reaper script cannot delete.'
    # )
    # parser_2.set_defaults(command='list_iam_actions')

    included_help = 'List of resource ID patterns to include in the form of A:B:C:D with A "*" ' \
                    'of a service name, B "*" or a region name, C "*" or a resource type name, ' \
                    'D a resource identifier pattern that can contains a wildcard like "prefix*. ' \
                    'You can specify multiple "--included" arguments, one for each pattern. ' \
                    'Default is "*:*:*:*" to include all possible resources.'
    excluded_help = 'List of resource ID patterns to include in the form of A:B:C:D with A "*" ' \
                    'of a service name, B "*" or a region name, C "*" or a resource type name, ' \
                    'D a resource identifier pattern that can contains a wildcard like "prefix*. ' \
                    'You can specify multiple "--excluded" arguments, one for each pattern. ' \
                    'Default is None to exclude no resource resources.'
    access_key_id_help = 'AWS access key. You must specify aws_secret_access_key.'
    secret_access_key_help = 'AWS secret key. You must specify aws_secret_key_id.'
    session_token_help = 'AWS _session token. You must provide aws_access_key_id and ' \
                         'aws_secret_access_key.'
    profile_name_help = 'Use the AWS credentials from the [profile_name] section of ' \
                        '~/.aws/credentials'
    regions_help = 'For some services, botocore might return an incomplete list of ' \
                   'regions that a service supports. Set to True to override the list ' \
                   'of supported regions returned by botocore, and try to delete ' \
                   'resources for that service in every possible region. '
    workers_help = 'Number of concurrent threads, or workers, that are processing an execution ' \
                   'plan. The default value is 20.'

    parser_3 = sub_parser.add_parser(
        'check_account',
        help='List the existing resources to delete in an AWS account.'
    )
    parser_3.add_argument('--included', action='append', help=included_help)
    parser_3.add_argument('--excluded', action='append', help=excluded_help)
    parser_3.add_argument('--aws_access_key_id', help=access_key_id_help)
    parser_3.add_argument('--aws_secret_access_key', help=secret_access_key_help)
    parser_3.add_argument('--aws_session_token', help=session_token_help)
    parser_3.add_argument('--profile_name', help=profile_name_help)
    parser_3.add_argument('--override_botocore_regions', action='store_true', help=regions_help)
    parser_3.add_argument('--nb_workers', type=int, help=workers_help)
    parser_3.set_defaults(command='check_account')

    min_passes_help = 'Minimum number of passes that the reaper script should run on this AWS ' \
                      'account to attempt deleting resources.'
    max_passes_help = 'The reaper script will stop run passes on the account, either when no ' \
                      'more new resources were deleted or failed to delete, or when the maximum ' \
                      'number of passes is reached.'

    parser_4 = sub_parser.add_parser(
        'clean_account',
        help='Delete the existing resources from an AWS account.'
    )
    parser_4.add_argument('--included', action='append', help=included_help)
    parser_4.add_argument('--excluded', action='append', help=excluded_help)
    parser_4.add_argument('--aws_access_key_id', help=access_key_id_help)
    parser_4.add_argument('--aws_secret_access_key', help=secret_access_key_help)
    parser_4.add_argument('--aws_session_token', help=session_token_help)
    parser_4.add_argument('--profile_name', help=profile_name_help)
    parser_4.add_argument('--override_botocore_regions', action='store_true', help=regions_help)
    parser_4.add_argument('--nb_workers', type=int, help=workers_help)
    parser_4.add_argument('--min_passes', type=int, help=min_passes_help)
    parser_4.add_argument('--max_passes', type=int, help=max_passes_help)
    parser_4.set_defaults(command='clean_account')

    parser_5 = sub_parser.add_parser(
        'get_execution_plan',
        help='Return an execution plan.'
    )
    parser_5.add_argument('--included', action='append', help=included_help)
    parser_5.add_argument('--excluded', action='append', help=excluded_help)
    parser_5.add_argument('--aws_access_key_id', help=access_key_id_help)
    parser_5.add_argument('--aws_secret_access_key', help=secret_access_key_help)
    parser_5.add_argument('--aws_session_token', help=session_token_help)
    parser_5.add_argument('--profile_name', help=profile_name_help)
    parser_5.set_defaults(command='get_execution_plan')

    args = parser.parse_args()

    logger = aws_reaper.tests.cli.common.get_cli_logger(debug=args.debug)

    try:
        if args.command == 'list_resource_types':
            resource_types = Reaper.list_supported_resource_types()
            logger.info(json.dumps(resource_types, indent=4))
            return

        # if args.command == 'list_iam_actions':
        #     iam_actions = Reaper.list_iam_actions()
        #     logger.info(json.dumps(iam_actions, indent=4, sort_keys=True))
        #     return

        reaper_kwargs = {}
        credentials = {}
        if args.aws_access_key_id is not None:
            credentials['aws_access_key_id'] = args.aws_access_key_id
        if args.aws_secret_access_key is not None:
            credentials['aws_secret_access_key'] = args.aws_secret_access_key
        if args.aws_session_token is not None:
            credentials['aws_session_token'] = args.aws_session_token
        if args.profile_name is not None:
            credentials['profile_name'] = args.profile_name
        reaper_kwargs.update(**credentials)
        if args.nb_workers is not None:
            reaper_kwargs['nb_workers'] = args.nb_workers

        reaper = Reaper(
            included_id_patterns=args.included, excluded_id_patterns=args.excluded,
            override_botocore_regions=args.override_botocore_regions, **reaper_kwargs
        )

        if args.command == 'check_account':
            result = reaper.check_account()
            if result['Completed'] is True:
                logger.info(json.dumps(result, indent=4, sort_keys=True))
                nb_errors = len(result['Errors']['Describe'])
                nb_resources = sum(
                    len(r_value) for r_value in result['ResourceIdsToDelete'].values()
                )
                logger.info('Resources to delete: %s, Errors: %s' % (nb_resources, nb_errors))
            return

        if args.command == 'clean_account':
            # Print account information
            try:
                session = boto3.session.Session(**credentials)
                client_iam = session.client('iam')
                client_sts = session.client('sts')
                aliases = client_iam.list_account_aliases()['AccountAliases']
                alias = aliases[0] if len(aliases) > 0 else ''
                caller_identity = client_sts.get_caller_identity()
                print('')
                print('##################################################')
                print('###   WARNING: THIS OPERATION IS IRREVOCABLE   ###')
                print('##################################################')
                print('Account ID:  %s' % caller_identity['Account'])
                print('User Arn:    %s' % caller_identity['Arn'])
                print('IAM alias:   %s' % alias)
                print('##################################################')
                print('')
            except Exception as e:
                message = 'Cannot get account information: %s' % str(e)
                logger.fatal(message)
                raise AwsReaperException(message)

            # Ask for confirmation
            if alias != '':
                expected = '%s %s' % (alias, random.randint(1, 100))
            else:
                expected = '%s %s' % (caller_identity['Account'], random.randint(1, 100))
            submitted = input('Check the information above and enter "%s" to confirm: ' % expected)
            if expected != submitted:
                logger.warning('Incorrect input')
                return

            kwargs = {}
            if args.min_passes:
                kwargs['min_passes'] = args.min_passes
            if args.min_passes:
                kwargs['max_passes'] = args.max_passes

            result = reaper.clean_account(**kwargs)
            if result['Completed'] is True:
                logger.info(json.dumps(result, indent=4, sort_keys=True))
                nb_errors = len(result['Errors']['Describe'])
                nb_errors += sum(len(r) for r in result['Errors']['Delete'].values())
                nb_resources = sum(len(r) for r in result['ResourceIdsDeleted'].values())
                logger.info('Resources deleted: %s, Errors: %s' % (nb_resources, nb_errors))
            return

        if args.command == 'get_execution_plan':
            result = reaper.get_execution_plan()
            logger.info(json.dumps(result, indent=4, sort_keys=True))
            return

    except AwsReaperException:
        pass
    except KeyboardInterrupt:
        logger.warning('Execution interrupted')
    except Exception as e:
        logger.fatal(str(e), exc_info=True)


if __name__ == '__main__':
    main()
