# -*- coding: utf-8 -*-

"""Python automation for Tessa 2.0."""

#*************************************************************************
#
# ADOBE CONFIDENTIAL
# ___________________
#
#  Copyright 2018 Adobe Systems Incorporated
#  All Rights Reserved.
#
# NOTICE:  All information contained herein is, and remains
# the property of Adobe Systems Incorporated and its suppliers,
# if any.  The intellectual and technical concepts contained
# herein are proprietary to Adobe Systems Incorporated and its
# suppliers and may be covered by U.S. and Foreign Patents,
# patents in process, and are protected by trade secret or copyright law.
# Dissemination of this information or reproduction of this material
# is strictly forbidden unless prior written permission is obtained=
# from Adobe Systems Incorporated.
#*************************************************************************

# All imports
from pprint import pprint

from collections import OrderedDict

from retrying import retry

import json

import os

import getopt

import sys

import requests

import pkg_resources


# CONSTANTS
PLATFORM = 'all'
TYPE = 'runtime'
BUILDTYPE = 'pip'
SCOPE = 'compile'
BUILDLANGUAGE = 'python'
HOST = 'https://snitch.corp.adobe.com:443'
CONTENT_TYPE = "application/json"

identifier = BUILDLANGUAGE+':'+BUILDTYPE+':{group}:{name}:{version}'


def do_freeze():
    """Get distributions in virtualenv. Alternative if requirements.txt not provided."""
    with open("requirements_to_tessa.txt", "w") as req_f:
        for pkg in pkg_resources.working_set.by_key:
            req_f.write(pkg+"=="+str(pkg_resources.get_distribution(pkg).version) + "\n")

    return "requirements_to_tessa.txt"


def read_file(fpath, project_data):
    """Read top level libraries from requirements file."""
    top_lib_list = []
    top_lib = []
    second_lib = []
    try:
        fhandler = open(fpath, 'r').read().splitlines()
    except Exception as e:
        pprint(e)
    else:
        for line in fhandler:
            pprint(line)
            if "==" in line:
                package = line.split("==")[0]
                version = line.split("==")[1]
                lib_identifier = identifier.format(group=project_data['vendor'],  name=package, version=version)
                top_lib_list.append(lib_identifier)
            else:
                pprint('Please check requirements.txt file format. Expected name==version')

    parent_identifier = identifier.format(group=project_data['vendor'], name=project_data['name'], version=project_data['version'])
    #top_lib_list = list(set(top_lib_list))
    top_lib_list = list(OrderedDict.fromkeys(top_lib_list))
    for item in top_lib_list:
        if parent_identifier != item:
            top_lib.append({'lib_identifier':item, 'parent_identifier': parent_identifier})

    second_lib = child_lib(top_lib)

    return top_lib+second_lib


def child_lib(child_lib):
    """Return secondary level libraries."""
    child_lib_list = []
    for entry in child_lib:
        try:
            dist = pkg_resources.get_distribution(entry['lib_identifier'].split(':')[3])
            if dist.version == entry['lib_identifier'].split(':')[4]:
                for req in dist.requires():
                    dep_identifier = identifier.format(group=entry['lib_identifier'].split(':')[2], name=req.project_name, version=pkg_resources.get_distribution(req.project_name).version)
                    p_identifier = identifier.format(group=entry['lib_identifier'].split(':')[2], name=entry['lib_identifier'].split(':')[3], version = entry['lib_identifier'].split(':')[4])
                    child_lib_list.append({'lib_identifier':dep_identifier, 'parent_identifier': list(OrderedDict.fromkeys([entry['parent_identifier'], p_identifier]))})
        except Exception as e:
            pprint(e)
    return child_lib_list


def tessa_lib_data(lib_list, project_data):
    """Return secondary or more level libraries data as Tessa 2.0 payload."""
    if lib_list is None:
        lib_list = []
    dl = {}
    dl_lib_list = []
    for entry in lib_list:
        dl.update({'type':TYPE})
        dl.update({'scope':SCOPE})
        dl.update({'vendor':project_data['vendor']})
        dl.update({'buildType':BUILDTYPE})
        dl.update({'buildLanguage':BUILDLANGUAGE})
        dl.update({'name': entry['lib_identifier'].split(':')[3]})
        dl.update({'version':entry['lib_identifier'].split(':')[4]})
        dl.update({'identifier':entry['lib_identifier']})
        if type(entry['parent_identifier']) is list:
            dl.update({'parents':entry['parent_identifier']})
        else:
            dl.update({'parents':[entry['parent_identifier']]})
        dl_lib_list.append(dl.copy())

    return dl_lib_list


def tessa_payload(project_data, lib_list):
    """Return payload data for Tessa 2.0."""
    if lib_list is None:
        lib_list = []
    payload_data = {
        "name": project_data['name'],
        "identifier": identifier.format(group=project_data['vendor'], name=project_data['name'], version=project_data['version']),
        "version": project_data['version'],
        "displayName": project_data['dispname'],
        "platform": PLATFORM,
        "vendor": project_data['vendor'],
        "buildType": BUILDTYPE,
        "buildLanguage": BUILDLANGUAGE,
        "libraries": lib_list,
        "metaDataUrl":project_data['url']
    }

    return payload_data


def del_product(project_data):
    """Mark product for deletion."""
    if set(('del_ident', 'client_name', 'client_version', 'apikey')).issubset(project_data):
        del_query = HOST+"/api/product/v1/"+project_data['del_ident']
        headers = {
            'x-tessa-apikey':project_data['apikey'],
            'x-client-name' :project_data['client_name'],
            'x-client-version':project_data['client_version']
            }
        try:
            del_resp = requests.delete(del_query, headers=headers)
        except Exception as e:
            pprint(e)
        else:
            if del_resp.status_code == 200:
                pprint('Confirmed. Product will be deleted if not modified in 15 days.')
            else:
                pprint(del_resp.text)
    else:
        pprint('Please check client name/version/product identifier/apienv are provided')


def sub_product(project_data):
    """Subscribe to product."""
    if set(('sublist', 'client_name', 'client_version', 'apikey')).issubset(project_data):
        data = {
            "subscribers" : project_data['sublist']
        }
        headers = {
            'x-tessa-apikey':project_data['apikey'],
            'x-client-name' :project_data['client_name'],
            'x-client-version':project_data['client_version']
        }

        sub_query = HOST+"/api/product/v1/"+project_data['ident']+'/subscribe'
        try:
            resp = requests.post(sub_query, headers=headers, data=json.dumps(data))
        except Exception as e:
            pprint(e)
        else:
            if resp.status_code == 200:
                pprint('Subscribed'+resp.text)
    else:
        pprint("subscription list is empty or automation client details not provided")

def send_to_tessa(project_data, data):
    """Send data to Tessa 2.0. Returns product identifier."""
    if data is None:
        data = {}
    identifier = ''
    try:
        response, session = make_post_call(project_data, data)
    except Exception as e:
        pprint(e)
    else:
        pprint(response)
        if response.status_code == 200:
            response_data = json.loads(response.text)
            pprint('Project entry created at '+response_data['identifier'])
            identifier = response_data['identifier']
            pprint(response_data['updatedAt'])
            session.headers.update({'Content-Type':'application/json'})
        else:
            pprint(response.text)
    return identifier

def exception_occurred(exception):
    pprint("Retrying as exception occurred")
    pprint(exception)
    return True

@retry(wait_exponential_multiplier=5000, stop_max_attempt_number=5, retry_on_exception=exception_occurred)
def make_post_call(project_data, data):
    error_codes = [500, 502, 503]
    session = requests.Session()
    session.headers.update({'x-tessa-apikey':project_data['apikey']})
    session.headers.update({'x-client-name':project_data['client_name']})
    session.headers.update({'x-client-version':project_data['client_version']})
    query = HOST+"/api/product/v1/"
    response = session.request("POST", query, headers={"content-type":CONTENT_TYPE}, data=json.dumps(data))
    if response.status_code in error_codes:
        raise Exception("Error received from server: %s %s" % (response.status_code, response.text))
    return (response, session)

def usage():
    """Available command line arguments."""
    msg = """
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
    -x --product_delete     Identifier of product to be deleted
    -i --product_identifier Identifier of product to subscribe to
    -m --more_levels        Need third and fourth level dependency data Y/N
    -h --help               Prints this
    """
    print(msg)


def get_args(argv):
    """Parse arguments provided and return project metadata."""
    project = {}
    subscriber_list = ''
    try:
        opts, args = getopt.getopt(argv, "n:v:u:g:d:r:y:z:a:s:i:x:m:h", ["product_name=", "product_version=", "product_url=", "product_vendor=", "product_dispname=", "product_reqfile=", "client_name=", "client_version=", "apienv=", "product_sublist=", "product_identifier=", "product_delete=", "more_levels=", "help"])
    except getopt.GetoptError:
        usage()
        sys.exit(2)
        pprint("CLI error. Check provided arguments")
    for opt, arg in opts:
        if opt in ('-n', 'product_name'):
            project['name'] = arg
        if opt in ('-v', 'product_version'):
            project['version'] = arg
        if opt in ('-u', 'product_url'):
            project['url'] = arg
        if opt in ('-g', 'product_vendor'):
            project['vendor'] = arg
        if opt in ('-d', 'product_dispname'):
            project['dispname'] = arg
        if opt in ('-r', 'product_reqfile'):
            project['reqfile'] = arg
        if opt in ('-y', 'X_CLIENT_NAME'):
            project['client_name'] = arg
        if opt in ('-z', 'X_CLIENT_VERSION'):
            project['client_version'] = arg
        if opt in ('-a', 'apienv'):
            project['apienv'] = arg
        if opt in ('-s', 'product_sublist'):
            subscriber_list = arg
        if opt in ('-i', 'product_identifier'):
            project['ident'] = arg
        if opt in ('-x', 'product_delete'):
            project['del_ident'] = arg
        if opt in ('-m', 'more_levels'):
            project['more_levels'] = arg
        elif opt in ('-h', '--help'):
            usage()
            sys.exit()

    if subscriber_list:
        project['sublist'] = list(OrderedDict.fromkeys(subscriber_list.split(',')))
        pprint(project['sublist'])
    return project


def main(argv):
    """Main."""
    all_libs_list = []
    req_file = ''

    project_data = get_args(argv)

    apikey = os.getenv(project_data['apienv'])
    if apikey is None:
        pprint('API key missing. Please provide correct env name')
        sys.exit()
    else:
        project_data['apikey'] = apikey

    if 'del_ident' in project_data:
        pprint("Product marked for deletion. Wait to confirm")
        del_product(project_data)
        sys.exit()

    if set(('name', 'version', 'url', 'vendor', 'apikey')).issubset(project_data):
        pprint("Continue")
    else:
        pprint("Insufficient arguments provided. Please check input")
        sys.exit()

    if not project_data['reqfile']:
        filename = do_freeze()
    else:
        filename = project_data['reqfile']

    default_list = read_file(filename, project_data)

    all_libs_list = tessa_lib_data(default_list, project_data)

    data = tessa_payload(project_data, all_libs_list)
    pprint(data)

    prod_id = send_to_tessa(project_data, data)

    if 'sublist' in project_data:
        if 'ident' not in project_data:
            project_data['ident'] = prod_id
        sub_product(project_data)


if __name__ == "__main__":
    main(sys.argv[1:])
