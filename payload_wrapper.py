import json
from flask import jsonify


class PayloadWrapper:
    def __init__(self):
        pass

    def success(self, payload=None, message=''):
        if payload is None:
            data = []
        elif isinstance(payload, list) is True:
            data = payload
        else:
            data = [payload]

        result = {
            "status": 'success',
            "hasErrors": False,
            "message": message,
            "length": len(data),
            "payload": data,
        }
        return result

    def pending(self, payload=None, message=''):
        if payload is None:
            data = []
        elif isinstance(payload, list) is True:
            data = payload
        else:
            data = [payload]

        result = {
            "status": 'pending',
            "hasErrors": False,
            "message": message,
            "length": len(data),
            "payload": data,
        }
        return result

    def error(self, message=''):

        result = {
            "status": 'error',
            "hasErrors": True,
            "message": message,
            "length": -1,
            "payload": [],
        }
        return result
        
    def headers(self):
        return {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Credentials': 'true',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Origin, X-Requested-With, Content-Type, Accept, Authorization',
        'Access-Control-Allow-Methods': 'POST, GET, PUT, DELETE, OPTIONS'}
       



# esponse.setHeader("Access-Control-Allow-Origin", "*");
# response.setHeader("Access-Control-Allow-Credentials", "true");
# response.setHeader("Access-Control-Allow-Methods", "GET,HEAD,OPTIONS,POST,PUT");
# response.setHeader("Access-Control-Allow-Headers", "Access-Control-Allow-Headers, Origin,Accept, X-Requested-With, Content-Type, Access-Control-Request-Method, Access-Control-Request-Headers");