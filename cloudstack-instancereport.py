#!/usr/bin/python

import urllib2
import urllib
import json
import hmac
import base64
import hashlib
import re
import datetime
import time
import socket
import os
import argparse
try:
    from elasticsearch import Elasticsearch
    from elasticsearch.helpers import bulk
except ImportError:
    print "It look like elasticsearch-py isn't installed. Please install it using pip install elasticsearch>=1.0.0,<2.0.0 or pip install elasticsearch<1.0.0. See http://elasticsearch-py.readthedocs.org/en/latest/ for more info"
try:
    from raven import Client
except ImportError:
    Client = None
    pass


def main():
    parser = argparse.ArgumentParser(description='This script connect to cloudstack API, list all vms with details and add  document for each VM in a given ES cluster index')
    parser.add_argument('-version', action='version', version='%(prog)s 1.0, Loic Lambiel exoscale')
    parser.add_argument('-acsurl', help='Cloudstack API URL', required=True, type=str, dest='acsurl')
    parser.add_argument('-acskey', help='Cloudstack API user key', required=True, type=str, dest='acskey')
    parser.add_argument('-acssecret', help='Cloudstack API user secret', required=True, type=str, dest='acssecret')
    parser.add_argument('-esindex', help='ES index name', required=True, type=str, dest='esindex')
    parser.add_argument('-esnodes', help='ES nodes list space separated', required=True, type=str, dest='esnodes')
    if Client is not None:
        parser.add_argument('-sentryapikey', help='Sentry API key', required=False, type=str, dest='sentryapikey')
    args = vars(parser.parse_args())
    return args


class BaseClient(object):

    def __init__(self, api, apikey, secret):
        self.api = api
        self.apikey = apikey
        self.secret = secret

    def request(self, command, args):
        args['apikey'] = self.apikey
        args['command'] = command
        args['response'] = 'json'

        params = []

        keys = sorted(args.keys())

        for k in keys:
            params.append(k + '=' + urllib.quote_plus(args[k]).replace("+", "%20"))

        query = '&'.join(params)

        signature = base64.b64encode(hmac.new(
            self.secret,
            msg=query.lower(),
            digestmod=hashlib.sha1
        ).digest())

        query += '&signature=' + urllib.quote_plus(signature)

        response = urllib2.urlopen(self.api + '?' + query)
        decoded = json.loads(response.read())

        propertyResponse = command.lower() + 'response'
        if propertyResponse not in decoded:
            if 'errorresponse' in decoded:
                raise RuntimeError("ERROR: " + decoded['errorresponse']['errortext'])
            else:
                raise RuntimeError("ERROR: Unable to parse the response")

        response = decoded[propertyResponse]
        result = re.compile(r"^list(\w+)s").match(command.lower())

        if result is not None:
            type = result.group(1)

            if type in response:
                return response[type]
            else:
                # sometimes, the 's' is kept, as in :
                # { "listasyncjobsresponse" : { "asyncjobs" : [ ... ] } }
                type += 's'
                if type in response:
                    return response[type]

        return response

    def listVirtualMachines(self, args={}):
        return self.request('listVirtualMachines', args)


def get_stats(args):

    ACSURL = args['acsurl']
    ACSKEY = args['acskey']
    ACSSECRET = args['acssecret']
    esindex = args['esindex']
    esnodes = args['esnodes']

    DOCTYPE = 'acs-instancereport'

    now = time.strftime("%Y.%m.%d")
    esindex = esindex + '-' + now

    # collect number of virtual machines
    cloudstack = BaseClient(ACSURL, ACSKEY, ACSSECRET)

    query_tmp = None
    querypage = 1
    querypagesize = 500
    virtualmachines = cloudstack.listVirtualMachines({
        'listall': 'true',
        'details': 'all',
        'page': str(querypage),
        'pagesize': str(querypagesize)
    })
    all_virtualmachines = []
    if len(virtualmachines) == querypagesize:
        query_tmp = virtualmachines
        while len(query_tmp) > 1:
            all_virtualmachines.extend(query_tmp)
            querypage = querypage + 1
            query_tmp = cloudstack.listVirtualMachines({
                'listall': 'true',
                'details': 'all',
                'page': str(querypage),
                'pagesize': str(querypagesize)
            })
    else:
        all_virtualmachines.extend(virtualmachines)
    virtualmachines = all_virtualmachines

    ESCLUSTERNODES = esnodes.split()
    es = Elasticsearch(ESCLUSTERNODES)
    scriptpath = os.path.realpath(__file__)

    timestamp = datetime.datetime.now()
    # create index and ignore if already exists
    es.indices.create(index=esindex, ignore=400)
    # create ES mappings
    es.indices.put_mapping(
        index=esindex,
        doc_type=DOCTYPE,
            body={
                DOCTYPE: {
                    'properties': {
                        'account': {
                            'type': 'text',
                        },
                        'id': {
                            'type': 'text',
                        },
                        'state': {
                            'type': 'keyword',
                        },
                        'cpunumber': {
                            'type': 'text',
                        },
                        'displayname': {
                            'type': 'keyword',
                        },
                        'hostname': {
                            'type': 'keyword',
                        },
                        'instancename': {
                            'type': 'keyword',
                        },
                        'memory': {
                            'type': 'text',
                        },
                        'name': {
                            'type': 'keyword',
                        },
                        'serviceofferingid': {
                            'type': 'text',
                        },
                        'serviceofferingname': {
                            'type': 'text',
                        },
                        'templateid': {
                            'type': 'text',
                        },
                        'templatedisplaytext': {
                            'type': 'text',
                        },
                        'zoneid': {
                            'type': 'text',
                        },
                        'zonename': {
                            'type': 'keyword',
                        }
                        'ipaddress': {
                            'type': 'text',
                        },
                        'macaddress': {
                            'type': 'text',
                        },
                        'securitygroupid': {
                            'type': 'text',
                        },
                        'securitygroupname': {
                            'type': 'text',
                        },
                        '@source_host': {
                            'type': 'text',
                        },
                        '@source': {
                            'type': 'text',
                        },
                        '@source_path': {
                            'type': 'text',
                        },
                        '@type': {
                            'type': 'text',
                        },
                        '@message': {
                            'type': 'text',
                        },
                        '@timestamp': {
                            'type': 'date'
                        }
                    }
                }
            },
        include_type_name=True
    )
    # create ES document
    if virtualmachines:
        records = []
        for virtualmachine in virtualmachines:
            vmaccount = virtualmachine['account']
            vmid = virtualmachine['id']
            vmstate = virtualmachine['state']
            vmcpunumber = virtualmachine['cpunumber']
            if 'displayname' in virtualmachine:
                vmdisplayname = virtualmachine['displayname']
            else:
                vmdisplayname = ''
            if virtualmachine['state'] == 'Running':
                vmhostname = virtualmachine['hostname']
            else:
                vmhostname = ''
            vminstancename = virtualmachine['instancename']
            vmmemory = virtualmachine['memory']
            vmname = virtualmachine['name']
            vmserviceofferingid = virtualmachine['serviceofferingid']
            vmserviceofferingname = virtualmachine['serviceofferingname']
            vmtemplateid = virtualmachine['templateid']
            vmtemplatedisplaytext = virtualmachine['templatedisplaytext']
            vmzoneid = virtualmachine['zoneid']
            vmzonename = virtualmachine['zonename']
            vmipaddress = []
            vmmacaddress = ''
            for nic in virtualmachine['nic']:
                if 'ipaddress' in nic:
                    vmipaddress.append(nic['ipaddress'])
                if 'macaddress' in nic:
                    vmmacaddress = nic['macaddress']
                if 'secondaryip' in nic:
                    for secondaryips in nic['secondaryip']:
                        vmipaddress.append(secondaryips['ipaddress'])
            vmipaddress = [str(r) for r in vmipaddress]
            vmipaddress = str(vmipaddress).replace("'", "").strip('[]')
            for securitygroup in virtualmachine['securitygroup']:
                vmsecuritygroupid = securitygroup['id']
                vmsecuritygroupname = securitygroup['name']
            sourcehost = socket.gethostname()
            # body
            doc = {
                'account': vmaccount,
                'id': vmid,
                'state': vmstate,
                'cpunumber': vmcpunumber,
                'displayname': vmdisplayname,
                'hostname': vmhostname,
                'instancename': vminstancename,
                'memory': vmmemory,
                'name': vmname,
                'serviceofferingid': vmserviceofferingid,
                'serviceofferingname': vmserviceofferingname,
                'templateid': vmtemplateid,
                'templatedisplaytext': vmtemplatedisplaytext,
                'zoneid': vmzoneid,
                'zonename': vmzonename,
                'ipaddress': vmipaddress,
                'macaddress': vmmacaddress,
                'securitygroupid': vmsecuritygroupid,
                'securitygroupname': vmsecuritygroupname,
                '@source_host': sourcehost,
                '@source_path': scriptpath,
                '@source': scriptpath,
                '@type': 'ACS-instancereport',
                '@message': 'ACS instance report for vm %s' % vmid,
                '@timestamp': timestamp
            }
            records.append(doc)

        # index documents
        bulk(es, records, index=esindex, doc_type=DOCTYPE)

# main
if __name__ == "__main__":
    args = main()
    try:
        get_stats(args)
    except Exception:
        if args['sentryapikey'] is None:
            raise
        else:
            client = Client(dsn=args['sentryapikey'])
            client.captureException()
