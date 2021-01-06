from datetime import datetime
from elastic_search_wrapper import ElasticSearchWrapper

# by default we connect to localhost:9200
es = ElasticSearchWrapper()

es.smoketest()

