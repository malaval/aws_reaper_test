==========
AWS Reaper
==========

AWS Reaper is a Python script that lists and deletes the resources contained an AWS account, for
a large set of resource types. For a complete list of AWS resource types that AWS Reaper can
delete, please visit `Supported resource types`_

.. _`Supported resource types`: https://github.com/malaval/aws_reaper_test/blob/master/docs/generated/resource_types.md

What is this for?
-----------------
It is currently not natively possible to restore an AWS account to its initial state and delete all
its resources, or to programmatically close an AWS account. This script helps to wipe a lot of AWS
resources. The typical use cases include:

* Sandbox environments where resources created by a sandbox user are deleted before the AWS account is provided to another sandbox user
* Cleaning development or personal AWS accounts to avoid unintended costs

Quick Start
-----------
First, install the library:

.. code-block:: sh

    $ pip install aws_reaper

Next, AWS Reaper can be used either via its command line tool ``aws_reaper``, or by integrating
the package into an existing Python script or application or your choice.

Example using the command line tool
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Use the following command to list the existing resources that AWS Reaper can delete from the AWS
account that corresponds to the ``default`` AWS CLI profile, and return the result into a file
``check.json``.

.. code-block:: sh

    $ aws_reaper check_account --profile_name default --output check.json

Use the following command to delete the supported resources from that same AWS account , and
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
    result_check = reaper.check_account()
    result_clean = reaper.clean_account()

Quick Start
-----------
