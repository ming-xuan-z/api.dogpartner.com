from flask import Flask, jsonify, request
from flask.wrappers import Response
from flast_httpauth import HTTPBasicAuth
from werkzeug.security import generate_password_hash, check_password_hash
from elasticsearch import Elasticsearch
import uuid

# Connect to Elasticsearch
es = Elasticsearch(["https://es-8xbmi48v.public.tencentelasticsearch.com:9200/"])
es.cluster.health(wait_for_status='yellow', request_timeout=1)

# Create the application instance
app = Flask(__name__)


class User():
    def __init__(self, username, password):
        self._id = str(uuid.uuid4())
        self.username = username
        self.password = password

class ESIndex():
    def __init__(self, index):
        self.index = index
    
    def put_doc(self, doc):
        res = es.index(index=self.index, body=doc)
        return res

    def get_doc(self, id):
        res = es.get(index=self.index, id=id)
        return res

    def search(self, query):
        res = es.search(index=self.index, body=query)
        return res


@app.route('/api/users', methods = ['POST'])
def new_user():
    user_index = ESIndex("user")
    username = request.json.get('username')
    password = request.json.get('password')
    if username is None or password is None:
        abort(Response("Username cannot be empty")) # missing arguments
    user = user_index.search({"query": {"term": {'username': username}}})
    if user['hits']['total'] > 0:
        abort(Response("Username already exits")) # existing user
    user = User(username, generate_password_hash(password))
    user_index.put_doc(user.__dict__)
    return jsonify({'username': user.username}), 201, {'Location': url_for('get_user', id = user._id, _external = True)}


@app.route('/api/users/<id>')
def get_user(id):
    user_index = ESIndex("user")
    user = user_index.get_doc(id)
    if not user:
        abort(Response("User not found")) # user not found
    return jsonify({'username': user['_source']['username']})


@auth.verify_password
def verify_password(username, password):
    user_index = ESIndex("user")
    user = user_index.search({"query": {"term": {"username": username}}})
    if not user:
        return False
    user = user["hits"]["hits"][0]["_source"]
    if not user:
        return False
    if not check_password_hash(user["password"], password):
        return False
    return user["username"]


if __name__ == '__main__':
    app.run(debug=True)

