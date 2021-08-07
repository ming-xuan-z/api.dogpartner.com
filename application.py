from flask import Flask, jsonify, request, abort, url_for
from flask.wrappers import Response
from werkzeug.exceptions import default_exceptions
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import generate_password_hash, check_password_hash
from elasticsearch import Elasticsearch
import uuid
import time

# Connect to Elasticsearch
es = Elasticsearch(["https://es-8xbmi48v.public.tencentelasticsearch.com:9200/"], http_auth=('elastic', 'Alandofl0ve!'))

# Create the application instance
app = Flask(__name__)
auth = HTTPBasicAuth()


class User():
    def __init__(self, username, password):
        self.uid = str(uuid.uuid4())
        self.username = username
        self.password = password
        self.__dict__ = {
            "uid": self.uid,
            "username": self.username,
            "password": self.password
        }

class Opening():
    def __init__(self, body):
        self.id = str(uuid.uuid4())
        self.created_at = int(time.time())
        self.title = body["title"]
        self.description = body["description"]
        self.start_time = body["start_time"]
        self.end_time = body["end_time"]
        self.address = body["address"]
        self.latitude = body["latitude"]
        self.longitude = body["longitude"]
        self.image_url = body["image_url"]
        self.image_path = body["image_path"]
        self.user_id = body["user_id"]
        self.username = body["username"]
        self.user_image = body["user_image"]
        self.paid = body["paid"]
        self.hourly_rate = body["hourly_rate"]


class ESIndex():
    def __init__(self, index):
        self.index = index
    
    def put_doc(self, id, doc):
        res = es.index(index=self.index, body=doc, id=id)
        return res

    def get_doc(self, id):
        res = es.get(index=self.index, id=id)
        return res

    def update_doc(self, id, doc):
        res = es.index(index=self.index, id=id, body=doc)
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
    if user['hits']['total']['value'] > 0:
        abort(Response("Username already exits")) # existing user
    user = User(username, generate_password_hash(password))
    user_index.put_doc(user.uid, user.__dict__)
    return jsonify({'username': user.username}), 201, {'Location': url_for('get_user', id = user.uid, _external = True)}


@app.route('/api/users/<id>')
def get_user(id):
    user_index = ESIndex("user")
    user = user_index.get_doc(id)
    if not user:
        abort(Response("User not found")) # user not found
    return jsonify({'username': user['_source']['username']})


@app.route('/api/users/<id>', methods = ['PUT'])
@auth.login_required
def update_user():
    id = auth.current_user.uid
    user_index = ESIndex("user")
    user = user_index.get_doc(id)
    if not user:
        abort(Response("User not found"))
    new_username = request.json.get('username')
    if new_username is not None:
        user["_source"]["username"] = new_username
        user_index.update_doc(id, user['_source'])
    

@auth.verify_password
def verify_password(username, password):
    user_index = ESIndex("user")
    user = user_index.search({"query": {"term": {"username": username}}})
    if not user:
        return False # user not found
    user = user["hits"]["hits"][0]["_source"]
    if not user:
        return False
    if not check_password_hash(user["password"], password):
        return False
    return user

if __name__ == '__main__':
    app.run(debug=True)

