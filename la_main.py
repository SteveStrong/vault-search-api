import os
import json
import logging

from flask import Flask, jsonify, render_template, request, url_for
from flask_restplus import Api, Resource, fields, reqparse
from flask_cors import CORS,cross_origin

from elastic_search_wrapper import ElasticSearchWrapper
from payload_wrapper import PayloadWrapper

app = Flask(__name__)
app.config['SECRET_KEY'] = 'the quick brown fox jumps over the lazy   dog'
app.config['CORS_HEADERS'] = 'Content-Type'

cors = CORS(app, resources={r"/lasearch/api": {"origins": "http://localhost:4200"}})
# cors = CORS(app, resources={r"lasearch/api/*": {"origins": "*"}})

# https://blog.miguelgrinberg.com/post/designing-a-restful-api-with-python-and-flask
# https://flask-restplus.readthedocs.io/en/stable/example.html
# https://flask-restplus.readthedocs.io/en/stable/swagger.html
# https://flask-restplus.readthedocs.io/en/stable/_modules/flask_restplus/reqparse.html


# https://github.com/noirbizarre/flask-restplus/issues/54
# so that /swagger.json is served over https

if os.environ.get('HTTPS'):
    @property
    def specs_for_url(self):
        return url_for(self.endpoint('specs'), _external=True, _scheme='https')

    Api.specs_url = specs_for_url

api = Api(app, 
        version='3.00', 
        title='Value Search API',
        description='Elastic Search for Vault ',
        )
ns = api.namespace('valuesearch/api/v1', description='Search for value data')

@ns.route('/')
class About(Resource):
    def options(self):
        pw = PayloadWrapper()
        return "OK", 200, pw.headers()

    def get(self):
        pw = PayloadWrapper()
        res = pw.success()
        return res, 200, pw.headers()


@ns.route('/healthcheck')
class Healthcheck(Resource):
    def get(self):
        pw = PayloadWrapper()
        es = ElasticSearchWrapper()
        res = pw.success(es,"healthcheck")
        return res, 200, pw.headers()

@ns.route('/smoketest')
class Stats(Resource):
    @api.hide
    def options(self):
        pw = PayloadWrapper()
        return "OK", 200, pw.headers()

    def get(self):
        pw = PayloadWrapper()
        try:
            es = ElasticSearchWrapper()
            hits, extra = es.smoketest()
            res = pw.success(hits,extra)
            return res, 200, pw.headers()

        except Exception as message:
            res = pw.error(message)
            return res, 400, pw.headers()

@ns.route('/stats/<string:indexName>')
class Stats(Resource):
    @api.hide
    def options(self):
        pw = PayloadWrapper()
        return "OK", 200, pw.headers()

    @ns.doc('query about an index in the catalog')
    def get(self, indexName):
        pw = PayloadWrapper()
        try:

            es = ElasticSearchWrapper()
            hits = es.stats(indexName)
            res = pw.success([hits])
            return res, 200, pw.headers()

        except Exception as message:
            # print(message)
            res = pw.error(message)
            return res, 400, pw.headers()

@ns.route('/case/<string:caseid>')  
class QueryCase(Resource):
    @api.hide
    def options(self):
        pw = PayloadWrapper()
        return "OK", 200, pw.headers()

    @ns.doc('search for a case with caseID')
    def get(self, caseid):
        pw = PayloadWrapper()

        try:

            es = ElasticSearchWrapper()
      
            indexName = 'la-document'

            queryBody = {
                "from" : 0, "size" : 1000,
                "query": {
                    "match": {
                        "caseID": {
                            "query": caseid
                            }
                        }
                    }
                }

            hits = es.search(indexName, queryBody)

            res = pw.success(hits)
            return res, 200, pw.headers()

        except Exception as message:
            print(message)
            res = pw.error(message)
            return res, 400, pw.headers()

general = api.model('general', {
    'rhetclass': fields.String(example=' ', required=False, description='The RhetRule as a filter, like FindingSentence EvidenceSentence'),
    'includeany': fields.String(example=' ', required=False, description='Search for sentences containing any of these words'),
    'includeall': fields.String(example=' ', required=False, description='Search for sentences containing all of these words'),
    'exactphrase': fields.String(example=' ', required=False, description='Search for sentences containing this exact phrase'),
    'excludeany': fields.String(example=' ', required=False, description='Exclude sentences containing any of these words'),
 })

## https://flask-restplus.readthedocs.io/en/stable/_modules/flask_restplus/fields.html

@ns.route('/query')  
class QuerySentence(Resource):
    @api.hide
    def options(self):
        pw = PayloadWrapper()
        return "OK", 200, pw.headers()

    @ns.doc('compound search for a sentence containing')
    # @cross_origin(origin='localhost',headers=['Content- Type','Authorization'])
    @ns.expect(general)
    def post(self):
        pw = PayloadWrapper()
        

        parser = reqparse.RequestParser()
        parser.add_argument('rhetclass', location='json')
        parser.add_argument('includeany', location='json')
        parser.add_argument('includeall', location='json')
        parser.add_argument('exactphrase', location='json')
        parser.add_argument('excludeany', location='json')
        args = parser.parse_args()

        try:
            rhetclass = args['rhetclass']
            includeany = args['includeany']
            includeall = args['includeall']
            exactphrase = args['exactphrase']
            excludeany = args['excludeany']

            es = ElasticSearchWrapper()
            indexName = 'la-sentence'

            mustPhrase = []
            if (len(includeany.strip()) > 0):
                q = {
                    "match": {
                        "text": {
                            "query": includeany,
                            "operator": 'or'
                        }
                    }
                }
                mustPhrase.append(q)

            if (len(includeall.strip()) > 0):
                q = {
                    "match": {
                        "text": {
                            "query": includeall,
                            "operator": 'and'
                        }
                    }
                }
                mustPhrase.append(q)

            if (len(exactphrase.strip()) > 0):
                q = {
                    "match_phrase": {
                        "text": {
                            "query": exactphrase,
                        }
                    }
                }
                mustPhrase.append(q)   

            filterPhrase = {}
            print(rhetclass)
            if rhetclass.find("Sentence") > -1:
                filterPhrase =  {
                            "match": {
                                "rhetClass": {
                                    "query" : rhetclass
                                }
                            }
                        }

            must_notPhrase = {}
            if (len(excludeany.strip()) > 0):
                must_notPhrase =  {
                            "match": {
                                "text": {
                                    "query" : excludeany
                                }
                            }
                        }

            boolPhrase = {}
            if (len(mustPhrase) > 0):
                boolPhrase['must'] = mustPhrase

            if (len(filterPhrase) > 0):
                boolPhrase['filter'] = filterPhrase

            if (len(must_notPhrase) > 0):
                boolPhrase['must_not'] = must_notPhrase

            queryBody = {
                    "from" : 0, "size" : 1000,
                    "query": {
                        "bool": boolPhrase
                    }
                }

            # print(queryBody)
                
           
            hits = es.search(indexName, queryBody)

            res = pw.success(hits)
            return res, 200, pw.headers()

        except Exception as message:
            res = pw.error(message)
            return res, 400, pw.headers()

simple = api.model('simple', {
    'rhetclass': fields.String(example=' ', required=False,description='The RhetRule as a filter'),
    'text': fields.String(example=' ', required=True, description='The text to search'),
    'queryrule': fields.String(example='or', required=False, description='OR: match any AND: match all')
})

@ns.route('/search')  
class SearchSentence(Resource):
    @api.hide
    def options(self):
        pw = PayloadWrapper()
        return "OK", 200, pw.headers()

    @ns.expect(simple)
    # @cross_origin(origin='localhost',headers=['Content- Type','Authorization'])
    def post(self):
        pw = PayloadWrapper()

        parser = reqparse.RequestParser()
        parser.add_argument('rhetclass', location='json')
        parser.add_argument('text', location='json')
        parser.add_argument('queryrule', location='json')
        args = parser.parse_args()


        try:

            rhetclass = args['rhetclass']
            text = args['text']
            queryrule = args['queryrule']
            if (len(queryrule.strip()) == 0):
                queryrule = 'or'

            es = ElasticSearchWrapper()
            indexName = 'la-sentence'

            queryBody = {
                "from" : 0, "size" : 1000,
                "query": {
                    "match": {
                        "text": {
                            "query": text,
                            "operator": queryrule
                            }
                        }
                    }
                }

            if rhetclass.find("Sentence") > -1:
                queryBody['query'] = {
                    "bool": {
                        "must": [
                                {
                                    "match":{
                                        "rhetClass": {
                                            "query" : rhetclass
                                        }
                                    }
                                },{
                                    "match": {
                                        "text": {
                                            "query": text,
                                             "operator": queryrule
                                        }
                                    }
                                }
                                ]
                            }
                    }
                
            print(queryBody)

            hits = es.search(indexName, queryBody)
            # print(hits)

            res = pw.success(hits)
            return res, 200, pw.headers()

        except Exception as message:
            res = pw.error(message)
            return res, 400, pw.headers()

@ns.route('/context/<string:context>')  
class SentencesWithContext(Resource):
    @api.hide
    def options(self):
        pw = PayloadWrapper()
        return "OK", 200, pw.headers()

    @ns.doc('search for other sentences in the same document and paragraph')
    def get(self, context):
        pw = PayloadWrapper()
        try:

            es = ElasticSearchWrapper()
            indexName = 'la-sentence'

            # https://stackoverflow.com/questions/37709100/how-do-i-do-a-partial-match-in-elasticsearch
            queryBody = {
                "from" : 0, "size" : 100,
                "query": {
                    "match": {
                        "context": {
                            "query": context
                            }
                        }
                    }
                }

            hits = es.search(indexName, queryBody)

            res = pw.success(hits)
            return res, 200, pw.headers()

        except Exception as message:
            res = pw.error(message)
            return res, 400, pw.headers()


def startup():
    # if local  host=('127.0.0.1')
    app.run(debug=True)
    # app.run(port=8000, threaded=False, host=('127.0.0.1'))
    # app.run(port=8000, threaded=False, host=('0.0.0.0'))



if __name__ == '__main__':
    startup()