==========
AWS Reaper
==========

AWS Reaper is a Python script that lists and deletes the resources contained an AWS account, for
a large set of resource types. For a complete list of AWS resource types that AWS Reaper can
delete, please visit `Supported resource types`_

.. _`Supported resource types`: https://github.com/malaval/aws_reaper_test/blob/master/docs/generated/resource_types.md

What is this for?
-----------------
It is currently not natively possible to restore an AWS account to its initial state, to delete all
its resources or close an AWS account programmatically. This script helps to wipe a lot of AWS
resources. The typical use cases include:

* Resetting an AWS account so it can be used as a sandbox environment
* Cleaning development or personal AWS accounts to avoid unexpected costs

Key characteristics
-------------------
Here are some key characteristics of AWS Reaper:

* AWS Reaper manages dependencies between resources. For example, security groups cannot be deleted until EC2 instances are still referencing a security group. That is why AWS Reaper does not attempt to delete security groups until EC2 instances are deleted.
* AWS Reaper uses multi-threading to parallelize API requests and make the execution faster.
* The execution can be interrupted after a certain period of time and resumed by passing the state returned by the previous execution. This is particularly useful to run AWS Reaper on AWS Lambda, because some resources, like CloudFront distributions, may take longer than 15 minutes to delete.

Quick Start
-----------
First, install the library:

.. code-block:: sh

    $ pip install aws_reaper

Installing the livrary also installs the command line tool. Next, AWS Reaper can be used either via
its command line tool ``aws_reaper``, or by integrating the package into an existing Python
script or application or your choice.

Example using the command line tool
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Use the following command to list the existing resources that AWS Reaper can delete from the AWS
account that corresponds to the ``default`` AWS CLI profile, and return the result into a file
``check.json``.

.. code-block:: sh

    $ aws_reaper check_account --profile_name default --output check.json

Use the following command to list and delete the supported resources from that same AWS account, and
return the result of this operation into a file ``clean.json``. You will be asked to enter a text
to confirm the request.

.. code-block:: sh

    $ aws_reaper clean_account --profile_name default --output clean.json

Example using the Python package
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
The following instructions imports the required modules, creates a ``Reaper`` instance that uses
the ``default`` AWS CLI profile, lists the existing resources that AWS Reaper can delete from
the AWS account, and finally delete the resources.

.. code-block:: python

    from aws_reaper import Reaper
    reaper = Reaper(profile_name='default')
    result_check = reaper.check_account()  # To list the resources to delete only
    result_clean = reaper.clean_account()  # To list and delete resources

Caution!
--------
AWS Reaper is a very destructive tool and the actions that it takes on your behalf are irrevocable.
Be careful while using it.

When using the command line tool ``aws-reaper`` you will be warned about the operation that you are
about to execute, and you will be asked to confirm by entering a text that contains the IAM alias,
or the AWS account ID if the IAM alias is not configured, and a random number between 1 and 100.

.. code-block:: text

    ##################################################
    ###   WARNING: THIS OPERATION IS IRREVOCABLE   ###
    ##################################################
    Account ID:  123456789012
    User Arn:    arn:aws:iam::123456789012:root
    IAM alias:   your-account-alias
    ##################################################
    Enter "your-account-alias 99" to confirm:

When using the Python package directly, you are responsible for taking the appropriate precautions
to avoid unintended cleaning operations.

Parameters
----------

Filtering resources to delete
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
You can filter the resources to delete by specifying the resource ID patterns that should be
included or excluded. By default, AWS Reaper deletes all possible resources and exclude no
resource.

The patterns are of the form ``a:b:c:d`` with ``a`` the identifier of a service or (e.g. ``ec2``)
``*``, ``b `` the name of an AWS region or ``*``, ``c`` the identifier of a resource type or
``*``, and ``d`` the identifier or name of the resource and you may use a wildcard character (e.g
. ``prefix-*``). Some examples:

* ``ec2:us-east-1:instance:*`` corresponds to the EC2 instances in the North Virginia region
* ``lambda:*:function:prefix*`` corresponds to the Lambda functions in any regions whose name starts with ``prefix-``

You can specify the resource ID patterns to include by passing one or more ``--included``
arguments to the command line tool (e.g. ``--included "ec2:*:*:*" --included "lambda:*:*:*"``, or
by passing an ``included`` keyword argument to the  ``Reaper`` init function (e.g.
``included=["ec2:*:*:*", "lambda:*:*:*"]``). Same approach to specify the resource ID patterns to
exclude by passing one or more ``--excluded`` arguments to the command line tool, or an
``excluded`` keyword argument to the ``Reaper`` init function.

Example to delete all EC2 and Lambda resources except in the North Virginia region, using the
command line tool:

.. code-block:: sh

    $ aws_reaper clean_account --profile_name default --included "ec2:*:*:*" --included
    "lambda:*:*:*" --excluded "*:us-east-1:*:*" --output clean.json

Using the Python package:

.. code-block:: python

    from aws_reaper import Reaper
    reaper = Reaper(
        profile_name='default',
        included=['ec2:*:*:*', 'lambda:*:*:*'],
        excluded=['*:us-east-1:*:*]
    )
    result_clean = reaper.clean_account()

Credentials
~~~~~~~~~~~
You must provide valid AWS credentials that AWS Reaper uses to list and delete resources:

* The name of an AWS CLI profile: ``--profile_name`` command line argument, or ``profile_name`` keyword argument
* Or an access key and a secret key (and optionally a session token): ``--aws_access_key_id``, ``--aws_secret_access_key`` and ``--aws_session_token`` command line argument, or ``aws_access_key_id``, ``aws_secret_access_key`` and ``aws_session_token`` keyword arguments.

Example for an access key and secret key, using the command line tool:

.. code-block:: sh

    $ aws_reaper clean_account --aws_access_key_id XXXXXXX --aws_secret_access_key XXXXXXX

Using the Python package:

.. code-block:: python

    from aws_reaper import Reaper
    reaper = Reaper(aws_access_key_id='XXXXXXX', aws_secret_access_key='XXXXXXX')
    result_clean = reaper.clean_account()

Logging
-------

Using the command line tool
~~~~~~~~~~~~~~~~~~~~~~~~~~~
The command line tool prints error and informational messages. You can print debug messages by
using the ``-d`` or ``--debug`` argument. Example of logs printed:

.. code-block:: text

    INFO New execution 8f927e6f-c5c7-4d5d-8350-9e262a87fe76
    INFO [PASS 1] 16 steps remaining
    INFO [worker5] [acm:eu-central-1:certificate] Deleted arn:aws:acm:eu-central-1:123456789012:certificate/12345678-90ab-cdef-1234-567890abcdef
    INFO [worker9] [acm:eu-west-2:certificate] Deleted arn:aws:acm:eu-west-2:123456789012:certificate/12345678-90ab-cdef-1234-567890abcdef
    INFO [worker11] [acm:eu-west-3:certificate] Deleted arn:aws:acm:eu-west-3:123456789012:certificate/12345678-90ab-cdef-1234-567890abcdef

Using the Python package
~~~~~~~~~~~~~~~~~~~~~~~~
AWS Reaper logs messages into the ``aws_reaper`` logger. You should configure at least one handler
to get the log messages. Here is an example below:

.. code-block:: python

    import logging
    logger = logging.getLogger('aws_reaper')
    logger.setLevel(logging.INFO)
    stream_handler = logging.StreamHandler()
    logger.addHandler(stream_handler)

Other resources
---------------
* `Frequently Asked Questions`_
* `Detailed user documentation`_
* `Contribute`_

.. _`Frequently Asked Questions`: https://github.com/malaval/aws_reaper_test/blob/master/docs/manual/faq.md
.. _`Detailed user documentation`: https://github.com/malaval/aws_reaper_test/blob/master/docs/manual/user_doc.md
.. _`Contribute`: https://github.com/malaval/aws_reaper_test/blob/master/docs/manual/contribute.md
