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

cors = CORS(app, resources={r"/vault/api/v1": {"origins": "http://localhost:3000"}})
# cors = CORS(app, resources={r"lasearch/api/*": {"origins": "*"}})

# https://blog.miguelgrinberg.com/post/designing-a-restful-api-with-python-and-flask
# https://flask-restplus.readthedocs.io/en/stable/example.html
# https://flask-restplus.readthedocs.io/en/stable/swagger.html
# https://flask-restplus.readthedocs.io/en/stable/_modules/flask_restplus/reqparse.html


# https://github.com/noirbizarre/flask-restplus/issues/54
# so that /swagger.json is served over https


# green open smoke-index                     r-oDpGRbQuSrApTBY-BP3A 5 1        1 0   9.8kb   4.9kb
# green open .kibana_-1610926851_vaultuser_1 _--jLgF_RmOLcRcMuf2Wjg 1 1        9 0 105.5kb  52.7kb
# green open vault-info                      _k3TFvCmRmq41tkpxZmBTw 5 1        4 0 720.9kb 360.4kb
# green open ais                             4K3IfR0WSOujlJhheKKGRQ 5 1   669895 0 284.5mb 142.2mb
# green open ais_full                        f3StJLnHS5KVje2PUx_3Mg 5 1  4867241 0   1.8gb 948.7mb
# green open tle_full                        u_xJnLrWQ2-EaIfxGl3kqA 5 1 10139772 0  17.3gb   8.6gb
# green open tle                             DMk9NvK5RFO_CTGhP0AEFw 5 1  2052060 0   3.7gb   1.8gb
# green open .kibana_1                       mkrlL4twQ-eIeE3EXEN2yQ 1 1      330 7 128.5kb  44.9kb
# green open .opendistro_security            CQg4kwIfQ1q5buPV2K6F_w 1 2        9 3 155.3kb  51.7kb


if os.environ.get('HTTPS'):
    @property
    def specs_for_url(self):
        return url_for(self.endpoint('specs'), _external=True, _scheme='https')

    Api.specs_url = specs_for_url

api = Api(app, 
        version='3.00', 
        title='SAIC Vault Search API',
        description='Elastic Search for Vault ',
        )
ns = api.namespace('vault/api/v1', description='Search for vault data')

@ns.route('/')
class About(Resource):
    def options(self):
        pw = PayloadWrapper()
        return "OK", 200, pw.headers()

    def get(self):
        pw = PayloadWrapper()
        res = pw.success()
        return res, 200, pw.headers()


@ns.route('/ping')
class Ping(Resource):
    def get(self):
        pw = PayloadWrapper()
        es = ElasticSearchWrapper()
        res = pw.success([],"OK")
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


# green open ais                             4K3IfR0WSOujlJhheKKGRQ 5 1   669895 0 284.5mb 142.2mb
# green open ais_full                        f3StJLnHS5KVje2PUx_3Mg 5 1  4867241 0   1.8gb 948.7mb
# green open tle_full                        u_xJnLrWQ2-EaIfxGl3kqA 5 1 10139772 0  17.3gb   8.6gb
# green open tle                             DMk9NvK5RFO_CTGhP0AEFw 5 1  2052060 0   3.7gb   1.8gb

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

@ns.route('/ships')  
class QueryAllShips(Resource):
    @api.hide
    def options(self):
        pw = PayloadWrapper()
        return "OK", 200, pw.headers()

    @ns.doc('search for all ships')
    def get(self):
        pw = PayloadWrapper()

        try:

            es = ElasticSearchWrapper()
      
            indexName = 'ais'

            queryBody = {
                "from": 0, "size": 5000,
                "query": {
                    "match_all": {}
                }
            }

            hits = es.search(indexName, queryBody)

            res = pw.success(hits)
            return res, 200, pw.headers()

        except Exception as message:
            print(message)
            res = pw.error(message)
            return res, 400, pw.headers()


@ns.route('/ship/<string:vessel_name>')  
class QueryShip(Resource):
    @api.hide
    def options(self):
        pw = PayloadWrapper()
        return "OK", 200, pw.headers()

    @ns.doc('search for a ships with vessel_name')
    def get(self, vessel_name):
        pw = PayloadWrapper()

        try:

            es = ElasticSearchWrapper()
      
            indexName = 'ais'

            queryBody = {
                "from": 0, "size": 1000,
                "query": {
                    "match": {
                        "vessel_name": {
                            "query": vessel_name
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


@ns.route('/satellites')  
class QueryAllSatellites(Resource):
    @api.hide
    def options(self):
        pw = PayloadWrapper()
        return "OK", 200, pw.headers()

    @ns.doc('search for all satellites')
    def get(self):
        pw = PayloadWrapper()

        try:

            es = ElasticSearchWrapper()
      
            indexName = 'tle'

            queryBody = {
                "from": 0, "size": 1000,
                "query": {
                    "match_all": {}
                }
            }

            hits = es.search(indexName, queryBody)

            res = pw.success(hits)
            return res, 200, pw.headers()

        except Exception as message:
            print(message)
            res = pw.error(message)
            return res, 400, pw.headers()


@ns.route('/satellites/<string:designator>')  
class QuerySatellite(Resource):
    @api.hide
    def options(self):
        pw = PayloadWrapper()
        return "OK", 200, pw.headers()

    @ns.doc('search for satellite with designator')
    def get(self, designator):
        pw = PayloadWrapper()

        try:

            es = ElasticSearchWrapper()
      
            indexName = 'tle'

            queryBody = {
                "from": 0, "size": 1000,
                "query": {
                    "match": {
                        "international_designator": {
                            "query": designator
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



def startup():
    # if local  host=('127.0.0.1')
    app.run(debug=True)
    # app.run(port=8000, threaded=False, host=('127.0.0.1'))
    # app.run(port=8000, threaded=False, host=('0.0.0.0'))



if __name__ == '__main__':
    startup()