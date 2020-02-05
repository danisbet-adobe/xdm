# Dependency automations for Tessa 2.0
Script to port dependencies for a project to Tessa 2.0.
Creates and updates project dependencies. Package dependencies of top-level dependencies are also ported.
Example -

requests==2.18.4
will be in Tessa 2.0 as
> - requests==2.18.4
>   - idna==2.6
>   - urllib3==1.22
>   - certifi==2017.7.27.1
>   - chardet==3.0.4


## Before using:
- Obtain Tessa API key from - https://snitch.corp.adobe.com/docs/#/API_key/get_api_auth_apitoken_v1
  - Service is Okta integrated so please login via browser to fetch API key
- If your project has 'requests' as a dependency
  - please maintain a 'requirements.txt' file having 'requests' as one of the dependencies
  - make sure to provide the file path in -r option
  - this is to avoid unncessary 'requests' from the upload script itself.
- pip install -r auto_requirements.txt


# Arguments
```bash
-n --product_name       Project name
-v --product_version    Project version
-u --product_url        Project repository url e.g. github
-g --product_vendor     Project group or vendor e.g.pypi
-d --product_dispname   Project display name
-r --product_reqfile    Path to requirements.txt file for project
-y --x_client_name      Automation client name as registered in Tessa 2.0
-z --x_client_version   Automation client version as registered in Tessa 2.0
-a --apienv             Environment variable name storing Tessa API key
-s --product_sublist    email ids separated by commas for product subscription
-i --product_identifier Identifier of product to subscribe to
-x --product_delete     Identifier of product to be deleted
-h --help               Prints this
```


# Use cases
## Create product and upload dependencies
```bash
python tessa_python_auto.py -n test_python -v test_version -u github.com -g pip -d test_python_display -r requirements.txt -a TESSA_APIKEYPY -y pip-client -z pip-client-version
```

## Subscribe to product
```bash
python tessa_python_auto.py -a TESSA_APIKEYPY -s example@adobe.com,sample.adobe.com -y pip-client -z 2.0 -i python:pip:pip:test_python:test_version
```

## Delete a product
```bash
python tessa_python_auto.py -a TESSA_APIKEYPY -y pip-client -z 2.0 -x python:pip:pip:test_python:test_version
```


### For python -
as installed in virtualenv during pip install.
Package dependencies can be verified using pip show <package_name>

Please note the script performs pip freeze for the project to collect libraries so run the script in virtual environment of the project to get correct library list.

## How it works -
- The script tessa_python_auto.py will run a pip freeze in the scope it is run.
- The scope should be your project virtualenv.
- It creates a file called requirements_to_tessa.txt in freeze format.
- It then uses pypi package information to get second level dependencies.
- Once top level and each of its dependencies are collected, it uses the api key variable specified in arguments to look up key to send this information to Tessa 2.0.
- If you want to verify what you will be sending, comment out send_to_tessa(project_data, data) and print data.
- It will attempt to retry 5 times within 5 minutes for the POST call to tessa in case of exceptions.
- Please note as inaccuracies were noticed in manually creating requirements.txt file, this script will automatically create one once run.
- If you feel particular libraries should not be included, contact tessa-core@adobe.com.


### python
- Project language is Python
- Project build is pip


## Issues:
Feedback welcome. Please open issues for bugs and recommendations.

## Interested to know other automations available for Tessa 2.0?
Check out - https://wiki.corp.adobe.com/display/asset/Tessa+Tracklib+Plugin+Dev
