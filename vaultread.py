from datetime import datetime
from elasticsearch import Elasticsearch


# https://www.elastic.co/guide/en/elasticsearch/reference/current/cat-indices.html
# https://www.elastic.co/guide/en/elasticsearch/reference/current/docker.html


# Endpoint = "https://search-vault-es-public-domain-5j637dz3uilvw5wvmx5zxo3axu.us-east-1.es.amazonaws.com/tle/_search?q=*"

#  https://search-vault-es-public-domain-5j637dz3uilvw5wvmx5zxo3axu.us-east-1.es.amazonaws.com/vault-info/_search?q=*

def elasticsearch_query():

    es = Elasticsearch()

    infoIndex = 'vault-info'

    query = {
        "query": {
            "match": {
                "name": {
                     "query": 'steve'
                }
            }
        }
    }

    print(query)

    res = es.search(index=infoIndex, body=query)
    print(res)

    for hit in res['hits']['hits']:
        print(hit["_source"])

# https://www.elastic.co/guide/en/elasticsearch/reference/current/search-request-body.html

    print("Got %d Hits:" % res['hits']['total']['value'])
     
elasticsearch_query()