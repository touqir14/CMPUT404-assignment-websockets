#!/usr/bin/env python
# coding: utf-8
# Copyright (c) 2013-2016 Touqir Sajed, Abram Hindle
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import flask
from flask import Flask, request
from flask_sockets import Sockets
import gevent
from gevent import queue
import time
import json
import os
from gevent import pywsgi
from geventwebsocket.handler import WebSocketHandler    

app = Flask(__name__)
sockets = Sockets(app)
app.debug = True

class World:
    def __init__(self):
        self.clear()
        # we've got listeners now!
        self.listeners = list()
        
    def add_set_listener(self, listener):
        self.listeners.append( listener )

    def update(self, entity, key, value):
        entry = self.space.get(entity,dict())
        entry[key] = value
        self.space[entity] = entry
        self.update_listeners( entity , entry)

    def updateEntities(self, entities):
        for k,v in entities.items():
            print "in entities"
            self.space[k] = v
            self.update_listeners(k,v)

    def set(self, entity, data):
        self.space[entity] = data
        self.update_listeners( entity , data)

    def update_listeners(self, entity, data):
        '''update the set listeners'''
        for listener in self.listeners:
            # listener(entity, self.get(entity))
            listener(entity, data)

    def clear(self):
        self.space = dict()

    def get(self, entity):
        return self.space.get(entity,dict())
    
    def world(self):
        return self.space

    def setWorld(self, world):
        self.space=world

    def getWorld(self):
        return json.dumps(self.space)


myWorld = World()        

def set_listener( entity, data ):
    msg = {}
    msg[entity] = data
    send_all_json(msg)

myWorld.add_set_listener( set_listener )

clients = list()

# This is Abram's code.
def send_all(msg):
    for client in clients:
        client.put( msg )

def send_all_json(obj):
    send_all( json.dumps(obj) )

# This is Abram's code.
class Client:
    def __init__(self):
        self.queue = queue.Queue()

    def put(self, v):
        self.queue.put_nowait(v)

    def get(self):
        return self.queue.get()


# This is Abram's code.
def read_ws(ws,client):
    '''A greenlet function that reads from the websocket and updates the world'''
    # XXX: TODO IMPLEMENT ME
    try:
        while True:
            msg = ws.receive()
            print "WS RECV: %s" % msg
            if (msg is not None):
                packet = json.loads(msg)
                myWorld.updateEntities(packet)
            else:
                break
    except:
        '''Done'''


@sockets.route('/subscribe')
# This is Abram's code.
def subscribe_socket(ws):
    '''Fufill the websocket URL of /subscribe, every update notify the
       websocket and read updates from the websocket '''
    # XXX: TODO IMPLEMENT ME
    client = Client()
    clients.append(client)
    g = gevent.spawn( read_ws, ws, client )    
    try:
        while True:
            # block here
            msg = client.get()
            ws.send(msg)

    except Exception as e:# WebSocketError as e:
        print "WS Error %s" % e
    
    finally:
        clients.remove(client)
        gevent.kill(g)


def flask_post_json():
    '''Ah the joys of frameworks! They do so much work for you
       that they get in the way of sane operation!'''
    if (request.json != None):
        return request.json
    elif (request.data != None and request.data != ''):
        return json.loads(request.data)
    else:
        return json.loads(request.form.keys()[0])

# The following 6 http method handler codes are taken from my assignment 4.

@app.route("/")
def hello():
    '''Return something coherent here.. perhaps redirect to /static/index.html '''
    return app.send_static_file('index.html')

@app.route("/json2.js")
def getJson2():
    return app.send_static_file('json2.js')

@app.route("/entity/<entity>", methods=['POST','PUT'])
def update(entity):
    '''update the entities via this interface'''
    entities=flask_post_json()
    # print entities
    for key in entities.keys():
        value=entities[key]
        myWorld.update(entity, key, value)

    if request.method == 'PUT':    
        return json.dumps(entities) # PUT returns the object that was put
    else:
        return myWorld.getWorld()

@app.route("/world", methods=['POST','GET','PUT'])    
def world():
    '''you should probably return the world here'''
    if request.method == 'GET':    
        return json.dumps(myWorld.world())
    elif request.method == 'POST' or request.method == 'PUT':
        world_new = flask_post_json()
        myWorld.setWorld(world_new)
        return myWorld.getWorld()


@app.route("/entity/<entity>", methods=['GET'])    
def get_entity(entity):
    '''This is the GET version of the entity interface, return a representation of the entity'''
    return json.dumps(myWorld.get(entity))

@app.route("/clear", methods=['POST','GET'])
def clear():
    '''Clear the world out!'''
    myWorld.clear()
    return "{}"


if __name__ == "__main__":
    ''' This doesn't work well anymore:
        pip install gunicorn
        and run
        gunicorn -k flask_sockets.worker sockets:app
    '''
    app.run()
