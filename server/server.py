#!/usr/bin/env python
from __future__ import print_function
import web
import re
import base64
import json
import sys
import os
import datetime
import time
import threading
import sys

from peewee import *
from w1thermsensor import W1ThermSensor
sensor = W1ThermSensor()



DATABASE = 'comfstat'
db = MySQLDatabase(DATABASE, user='comfstat',passwd='CjyuF39cY=bo')


urls = ('/login','Login',
 '/environment','Environment',
 '/user', 'User',
 '/vote', 'Vote',
 '/polar', 'Polar',
 '/temperature', 'Temperature',
 '/humidity', 'Humidity',
 '/battery', 'Battery',
 '/location', 'Location')


class User(Model):
    username = CharField(max_length=255, unique=True)
    sex = CharField(max_length=255)
    weight = IntegerField()
    height = IntegerField()
    password = CharField(max_length=255)
    birthday = DateTimeField()

    class Meta:
        """docstring for Meta"""
        database = db

    def POST(self):
        try:
            print_icon()
            data = web.data()
            message = json.loads(data)
            username = message['username']
            sex = message['sex']
            w = message['weight']
            h = message['height']
            password = message['password']
            bd = getFormattedDate(int(message['birthday']))

            user = {'username': username, 'sex': sex, 'weight': int(w), 'height': int(h), 'password': password, 'birthday': bd}
            user_id = add_user(user)

            web.header('Content-Type', 'application/json')
            env_values = {'id': user_id}
            web.ctx.status = '200 OK'
            return json.dumps(env_values)
            
        except IntegrityError:
            web.ctx.status = '409 Conflict'
            return
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print(exc_type, fname, exc_tb.tb_lineno)

    def GET(self):
        print_icon()
        auth = web.ctx.env.get('HTTP_AUTHORIZATION')
        authreq = False
        if auth is None:
            authreq = True
        else:
            auth = re.sub('^Basic ','',auth)
            username,password = base64.decodestring(auth).split(':')
            db_user = User.get(User.username == username)
            #print db_user.id, db_user.username, db_user.password
            sys.stderr.write(username +" " +password)
            if (username == db_user.username and password == db_user.password):
                #print "username and password correct"
                web.header('Content-Type', 'application/json')
                env_values = {'id': db_user.id}
                return json.dumps(env_values)
            else:
                authreq = True

        if authreq:
            web.header('WWW-Authenticate','Basic realm="Auth example"')
            web.ctx.status = '401 Unauthorized'
            return

def add_user(user):
    with db.transaction():
        user = User.create(
            username=user['username'],
            sex=user['sex'],
            weight=user['weight'],
            height=user['height'],
            password=user['password'],
            birthday=user['birthday']
        )
        return user.id

class Vote(Model):
    user = ForeignKeyField(User)
    comfort = IntegerField()
    temperature = FloatField()
    creation_date = DateTimeField()

    class Meta(object):
        """docstring for Meta"""
        database = db

    def POST(self):
        try:
            print_icon()
            data = web.data()
            message = json.loads(data)
            cd = getFormattedDate(int(message['creation_date']))
            cf = message['comfort']
            uid = message['user_id']

            t = sensor.get_temperature()
            t = round(t, 1)

            #print cd, cf, uid
            vote = {'user_id' : uid, 'comfort': int(cf), 'temperature': t, 'creation_date': cd}
            add_vote(vote)
            return
        except Exception as e:
            #print e
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print(exc_type, fname, exc_tb.tb_lineno)

    def GET(self):
        query = (Vote.select(User.id, User.username ,Vote.comfort, Vote.temperature, Vote.creation_date)
         .join(User)
         .order_by(Vote.creation_date.desc())  # Get the most recent votes.
         .limit(10))

        data = {}
        i = 0
        for entry in query:
            #print entry
            entry_data = {}
            entry_data['comfort'] = entry.comfort
            entry_data['creation_date'] = entry.creation_date.strftime("%Y-%m-%d %H:%M:%S")
            entry_data['id'] = entry.user.id
            entry_data['username'] = entry.user.username
            entry_data['temperature'] = entry.temperature
            data[str(i)] = entry_data
            #print entry_data
            i+=1
        return json.dumps(data, sort_keys=True)
      
def add_vote(vote):
    with db.transaction():
        Vote.create(
            user=vote['user_id'],
            comfort=vote['comfort'],
            temperature=vote['temperature'],
            creation_date=vote['creation_date'])

class Environment(Model):
    user = ForeignKeyField(User)
    temperature = FloatField()
    humidity = FloatField()
    heart_rate = IntegerField()
    battery = FloatField()
    elapsed_time=FloatField()
    accuracy=CharField(max_length=255)
    creation_date = DateTimeField()

    class Meta(object):
        """docstring for Meta"""
        database = db

    def GET(self):
        print_icon()
        web.header('Content-Type', 'application/json')
        t = sensor.get_temperature()
        p = 0
        h = 0

        t = round(t, 1)
        p = round(p, 1)
        h = round(h, 1)

        env_values = {'temperature':t,'pressure':p, 'humidity':h}
        return json.dumps(env_values)

    def POST(self):
        try:
            print_icon()
            data = web.data()
            message = json.loads(data)
            hr = message['heart_rate']
            cd = getFormattedDate(message['time'])
            bt = message['battery']
            uid = message['user_id']
            et = message['elapsed_time']
            acc = message['accuracy']

            t = sensor.get_temperature()
            p = 0
            h = 0

            t = round(t, 1)
            p = round(p, 1)
            h = round(h, 1)

            env = { 'user_id': uid , 'temperature': t, 'humidity': h, 'heart_rate': hr , 'battery': bt, 'creation_date': cd , 'elapsed_time': et, 'accuracy': acc}
            add_env(env)
            return
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print(exc_type, fname, exc_tb.tb_lineno)

class Polar(Model):
    user = ForeignKeyField(User)
    mobile_id = IntegerField()
    heart_rate = IntegerField()
    rr_interval = BlobField()
    comfort = IntegerField()
    temperature = FloatField()
    creation_date = DateTimeField()
    server_date = DateTimeField()

    class Meta(object):
        """docstring for Meta"""
        database = db

    def POST(self):
        try:
            print_icon()
            data = web.data()
            message = json.loads(data)
            uid = message['user_id']
            polar_values = message['polar_values']

            #print uid
            #print polar_values
            #print type(polar_values)

            for polar in polar_values:
                add_polar(uid, polar)
                #print polar['_id'], polar['heartRate'],polar['rrInterval'], getFormattedDate(int(polar['creationDate']))

            return
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print(exc_type, fname, exc_tb.tb_lineno)

def add_polar(uid, polar):
    with db.transaction():
        Polar.create(
            user=uid,
            mobile_id=polar['_id'],
            heart_rate=polar['heartRate'],
            rr_interval=polar['rrInterval'],
            comfort=0,
            temperature=0.0,
            creation_date=getFormattedDate(int(polar['creationDate'])),
            server_date=getCurrentTime()
            )


class Temperature(Model):
    user = ForeignKeyField(User)
    mobile_id = IntegerField()
    temperature = FloatField()
    creation_date = DateTimeField()
    server_date = DateTimeField()

    class Meta(object):
        """docstring for Meta"""
        database = db

    def POST(self):
        try:
            print_icon()
            data = web.data()
            message = json.loads(data)
            uid = message['user_id']
            temperature_values = message['temperature_values']

            for temperature in temperature_values:
                add_temperature(uid, temperature)
                #print temperature['_id'], temperature['degrees'], getFormattedDate(int(temperature['creationDate']))

            return
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print(exc_type, fname, exc_tb.tb_lineno)

def add_temperature(uid, temperature):
    with db.transaction():
        Temperature.create(
            user=uid,
            mobile_id=temperature['_id'],
            temperature=temperature['degrees'],
            creation_date=getFormattedDate(int(temperature['creationDate'])),
            server_date=getCurrentTime()
            )

class Humidity(Model):
    user = ForeignKeyField(User)
    mobile_id = IntegerField()
    value = FloatField()
    creation_date = DateTimeField()
    server_date = DateTimeField()

    class Meta(object):
        """docstring for Meta"""
        database = db

    def POST(self):
        try:
            print_icon()
            data = web.data()
            message = json.loads(data)
            uid = message['user_id']
            humidity_values = message['humidity_values']

            for humidity in humidity_values:
                add_humidity(uid, humidity)
                #print humidity['_id'], humidity['value'], getFormattedDate(int(humidity['creationDate']))

            return
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print(exc_type, fname, exc_tb.tb_lineno)

def add_humidity(uid, humidity):
    with db.transaction():
        Humidity.create(
            user=uid,
            mobile_id=humidity['_id'],
            value=humidity['value'],
            creation_date=getFormattedDate(int(humidity['creationDate'])),
            server_date=getCurrentTime()
            )

class Battery(Model):
    user = ForeignKeyField(User)
    mobile_id = IntegerField()
    level = IntegerField()
    creation_date = DateTimeField()
    server_date = DateTimeField()

    class Meta(object):
        """docstring for Meta"""
        database = db

    def POST(self):
        try:
            print_icon()
            data = web.data()
            message = json.loads(data)
            uid = message['user_id']
            battery_values = message['battery_values']

            for battery in battery_values:
                add_battery(uid, battery)
                #print battery['_id'], battery['level'], getFormattedDate(int(battery['creationDate']))

            return
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print(exc_type, fname, exc_tb.tb_lineno)

def add_battery(uid, battery):
    with db.transaction():
        Battery.create(
            user=uid,
            mobile_id=battery['_id'],
            level=battery['level'],
            creation_date=getFormattedDate(int(battery['creationDate'])),
            server_date=getCurrentTime()
            )

class Location(Model):
    user = ForeignKeyField(User)
    mobile_id = IntegerField()
    connected_to = TextField()
    available_wifi = TextField()
    creation_date = DateTimeField()
    server_date = DateTimeField()

    class Meta(object):
        """docstring for Meta"""
        database = db

    def POST(self):
        try:
            data = web.data()
            message = json.loads(data)
            uid = message['user_id']
            wifi_values = message['wifi_values']

            for wifi in wifi_values:
                add_wifi(uid, wifi)

            return
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print(exc_type, fname, exc_tb.tb_lineno)

def add_wifi(uid, wifi):
    with db.transaction():
        Location.create(
            user=int(uid),
            mobile_id=wifi['_id'],
            connected_to=str(wifi['connectedTo']),
            available_wifi=wifi['availableWifi'],
            creation_date=getFormattedDate(int(wifi['creationDate'])),
            server_date=getCurrentTime()
            )

def getFormattedDate(inputDate):
    return datetime.datetime.fromtimestamp(inputDate).strftime('%Y-%m-%d %H:%M:%S')

def getCurrentTime():
    time.ctime()
    return time.strftime('%Y-%m-%d %H:%M:%S')


def add_env(env):
    with db.transaction():
        Environment.create(
            user=env['user_id'],
            temperature=env['temperature'],
            humidity=env['humidity'],
            heart_rate=env['heart_rate'],
            battery=env['battery'],
            elapsed_time=env['elapsed_time'],
            accuracy=env['accuracy'],
            creation_date=env['creation_date']
            )

def print_icon():
    #sense.show_letter("!",text_colour=[0, 0, 0], back_colour=[0, 0, 255])
    time.sleep(1)
    #sense.clear()


db.connect()
db.create_tables([User, Vote, Environment, Polar, Temperature, Humidity, Battery, Location], safe=True)
application = web.application(urls, globals()).wsgifunc()
