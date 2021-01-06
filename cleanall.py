# Imports of import.
import json
import os

from datetime import datetime
from elastic_search_wrapper import ElasticSearchWrapper

# https://www.elastic.co/guide/en/elasticsearch/reference/current/cat-indices.html
# https://www.elastic.co/guide/en/elasticsearch/reference/current/docker.html



def elasticsearch_clean():

    #  https://elasticsearch-py.readthedocs.io/en/master/
    # by default we connect to localhost:9200
    es = ElasticSearchWrapper()

#   https://search-vault-es-public-domain-5j637dz3uilvw5wvmx5zxo3axu.us-east-1.es.amazonaws.com/_cat/indices
    
    es.delete_index('vault-info')
    es.delete_index('la-document')
    es.delete_index('la-sentence')
    es.delete_index('vault-index')
    es.delete_index('steve-index')
    es.delete_index('smoke-index')
    es.delete_index('la-info')
    es.delete_index('vault-info')

elasticsearch_clean()
