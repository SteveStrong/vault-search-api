# Imports of import.
import json
import os

from datetime import datetime
from elastic_search_wrapper import ElasticSearchWrapper

# https://www.elastic.co/guide/en/elasticsearch/reference/current/cat-indices.html
# https://www.elastic.co/guide/en/elasticsearch/reference/current/docker.html



def elasticsearch_publish():

    #  https://elasticsearch-py.readthedocs.io/en/master/
    # by default we connect to localhost:9200
    es = ElasticSearchWrapper()


    infoIndex = 'vault-info'
    es.delete_index(infoIndex)
    
    es.create_index(infoIndex)  # ignore if exist
    

    
    
    # Getting the list of files in <data_path>:
    data_path = './data/vault'
    list_of_files = os.listdir(data_path)

    # ...and creating new lists for the texts of the sentences...
    documentCount = 0
    
    print(list_of_files)
    # Using a for-loop to iterate over the filenames...
    for filename in list_of_files:
        print ( f"{data_path}/{filename}" )

        # ... and opening the given filename...
        file = open(f"{data_path}/{filename}")
        
        try:
            # ...using the json file loader to translate the json data...
            data = json.load(file)
            res = es.add_item(infoIndex, documentCount, data)

            documentCount += 1

        except Exception as ex:
            print(ex)
            
elasticsearch_publish()
