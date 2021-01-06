from flask import Flask
from flask_restplus import Resource, Api
from payload_wrapper import PayloadWrapper

app = Flask(__name__)                  #  Create a Flask WSGI application
api = Api(app)                         #  Create a Flask-RESTPlus API

@api.route('/hello')                   #  Create a URL route to this resource
class HelloWorld(Resource):  #  Create a RESTful resource
    def options(self):
        pw = PayloadWrapper()
        return "OK", 200, pw.headers()

    def get(self):
        pw = PayloadWrapper()
        res = pw.pending([{'hello': 'world'}], "things are pending")
        return res, 200, pw.headers()


if __name__ == '__main__':
    app.run(debug=True)
    
