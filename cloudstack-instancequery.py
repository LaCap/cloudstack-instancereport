#!/usr/bin/python

import sys, getopt, argparse

try:
    from elasticsearch import Elasticsearch
except ImportError:
    print "It look like elasticsearch-py isn't installed. Please install it using pip install elasticsearch>=1.0.0,<2.0.0 or pip install elasticsearch<1.0.0. See http://elasticsearch-py.readthedocs.org/en/latest/ for more info"
    sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description='This script output VMs ID based on a given ES query for cloudstack-instancereport. To generate the ES query, go to the HEAD ES plugin (xxx/_plugin/head/index.html, Structured Query tab, select the corresponding index, build your query from acs-instancereport.* fields and hit search. Click the Show Raw JSON to get the query. Beware of the size in the query which must likely be removed')
    parser.add_argument('-version', action='version', version='%(prog)s 1.0, Loic Lambiel exoscale')
    parser.add_argument('-esindex', help='ES index name', required=True, type=str, dest='esindex')
    parser.add_argument('-esnodes', help='ES nodes list space separated', required=True, type=str, dest='esnodes')
    parser.add_argument('-esquery', help='ES query between single quotes', required=True, type=str, dest='esquery')
    args = vars(parser.parse_args())
    return args



def get_docs(args):

    esindex = args['esindex']
    esnodes = args['esnodes']
    esquery = args['esquery']


    ESCLUSTERNODES = esnodes.split()
    es = Elasticsearch(ESCLUSTERNODES)
    
    res = es.search(index=esindex, body=esquery)

    print("Got %d Hits:" % res['hits']['total'])
    for hit in res['hits']['hits']:
        for items, value in hit.iteritems():
            if type(value) is dict:
                vmmid = value["id"]
                print vmmid


#main
if __name__ == "__main__":
    args = main()
    get_docs(args)

