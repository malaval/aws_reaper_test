import argparse
import json

import aws_reaper.tests.cli.common
from aws_reaper.tests.create_resources.main import Creator

# Fix Python 2
from aws_reaper.common.exceptions import AwsReaperException

try:
    # noinspection PyShadowingBuiltins,PyUnresolvedReferences
    input = raw_input
except NameError:
    pass


def main():
    parser = argparse.ArgumentParser(description='Create test resources for AWS Reaper')
    parser.add_argument('-d', '--debug', action='store_true')
    sub_parser = parser.add_subparsers(title='commands')

    parser_1 = sub_parser.add_parser(
        'list_resource_types',
        help='List the types of resources that the creator script currently supports.'
    )
    parser_1.set_defaults(command='list_resource_types')

    included_help = 'List of patterns of resources to create in the form of A:B:C with A "*" ' \
                    'of a service name, B "*" or a region name, C "*" or a resource type name. ' \
                    'You can specify multiple "--included" arguments, one for each pattern. ' \
                    'Default is "*:*:*" to create all possible resources.'
    access_key_id_help = 'AWS access key. You must specify aws_secret_access_key.'
    secret_access_key_help = 'AWS secret key. You must specify aws_secret_key_id.'
    session_token_help = 'AWS _session token. You must provide aws_access_key_id and ' \
                         'aws_secret_access_key.'
    profile_name_help = 'Use the AWS credentials from the [profile_name] section of ' \
                        '~/.aws/credentials'
    workers_help = 'Number of concurrent threads, or workers, that are processing an execution ' \
                   'plan. The default value is 20.'

    parser_2 = sub_parser.add_parser(
        'create_resources',
        help='Create test resources in an AWS account.'
    )
    parser_2.add_argument('--included', action='append', help=included_help)
    parser_2.add_argument('--aws_access_key_id', required=False, help=access_key_id_help)
    parser_2.add_argument('--aws_secret_access_key', required=False, help=secret_access_key_help)
    parser_2.add_argument('--aws_session_token', required=False, help=session_token_help)
    parser_2.add_argument('--profile_name', required=False, help=profile_name_help)
    parser_2.add_argument('--nb_workers', help=workers_help)
    parser_2.set_defaults(command='create_resources')

    parser_3 = sub_parser.add_parser(
        'get_execution_plan',
        help='Return an execution plan.'
    )
    parser_3.add_argument('--included', action='append', help=included_help)
    parser_3.add_argument('--aws_access_key_id', required=False, help=access_key_id_help)
    parser_3.add_argument('--aws_secret_access_key', required=False, help=secret_access_key_help)
    parser_3.add_argument('--aws_session_token', required=False, help=session_token_help)
    parser_3.add_argument('--profile_name', required=False, help=profile_name_help)
    parser_3.set_defaults(command='get_execution_plan')

    args = parser.parse_args()
    logger = aws_reaper.tests.cli.common.get_cli_logger(debug=args.debug)

    try:

        if args.command == 'list_resource_types':
            resource_types = Creator.list_supported_resource_types()
            logger.info(json.dumps(resource_types, indent=4))
            return

        creator_kwargs = {}
        if args.aws_access_key_id is not None:
            creator_kwargs['aws_access_key_id'] = args.aws_access_key_id
        if args.aws_secret_access_key is not None:
            creator_kwargs['aws_secret_access_key'] = args.aws_secret_access_key
        if args.aws_session_token is not None:
            creator_kwargs['aws_session_token'] = args.aws_session_token
        if args.profile_name is not None:
            creator_kwargs['profile_name'] = args.profile_name
        if args.nb_workers is not None:
            creator_kwargs['nb_workers'] = args.nb_workers

        creator = Creator(included=args.included, **creator_kwargs)

        if args.command == 'create_resources':
            result = creator.create_resources()
            if result['Completed'] is True:
                logger.info(json.dumps(result, indent=4, sort_keys=True))
                nb_errors = len(result['Errors']['Create'])
                nb_resources = sum(len(r_value) for r_value in result['ResourcesCreated'].values())
                logger.info('Resources created: %s, Errors: %s' % (nb_resources, nb_errors))
            return

        if args.command == 'get_execution_plan':
            result = creator.get_execution_plan()
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
