#!/usr/bin/python3
import pandas as pd
import numpy as np
import requests
import base64
from datetime import datetime
import time
import logging
import json

logging.basicConfig(filename='app.log', filemode='w',level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")
logging.getLogger().addHandler(logging.StreamHandler())

BASE_URL = 'https://covi.int2.real.com{0}'
PEOPLE_URL = BASE_URL.format("/people?insert=true&update=false&merge=false")
PEOPLE_URL = PEOPLE_URL+"&detect-age=false&detect-gender=false&detect-sentiment=false"
PEOPLE_URL = PEOPLE_URL+"&source=batchImport&site={0}&source={1}"
UPDATE_PEOPLE_URL = BASE_URL.format("/people/{}")

KEY_HEADER_AUTHORIZATION='X-RPC-AUTHORIZATION'
KEY_HEADER_DIRECTORY='X-RPC-DIRECTORY'
IMG_PATH = 'images/{0}'

user_id = 'userid'
passwd = 'passwd'
directory = 'directory'
site='test'
source = 'pythonBatch'

def createHeader(user_id, password, directory):
    enconding = 'utf-8'
    encode_password =  base64.b64encode(bytes(password, enconding)).decode(enconding)
    header_auth = "{0}:{1}".format(user_id, encode_password)
    return {
        'Content-Type': 'application/octet-stream',
        KEY_HEADER_AUTHORIZATION : header_auth,
        KEY_HEADER_DIRECTORY : directory
    }

def build_person(header, name, person_type, external_id, age, gender):
    a_header = {}
    a_header.update(header)
    if not isEmpty(name):
        a_header.update({
            'X-RPC-PERSON-NAME' : str(name)
        })
    if not isEmpty(person_type):
        a_header.update({
            'X-RPC-PERSON-TYPE' : str(person_type)
        })
    if not isEmpty(external_id):
        a_header.update({
            'X-RPC-EXTERNAL-ID' : str(external_id)
        })
    if not isEmpty(age):
        a_header.update({
            'X-RPC-AGE' : str(age)
        })
    if not isEmpty(gender):
        a_header.update({
            'X-RPC-GENDER' : str(gender)
        })
    return a_header

def isEmpty(field):
    return field is None or field == '' or pd.isnull(field)

def create_person(sess, header, params, upload_file):
    post_url = PEOPLE_URL.format(site, source)
    header.update({
        'Content-Type': 'application/octet-stream'
    })
    with sess.post(post_url,  headers=header, data=upload_file) as response:
        person = response.json()['identifiedFaces']
        if(len(person) == 1):
            logging.info('successfully registered {}'.format(upload_file.name))
            update(sess, header, person[0], 'threat')
        elif (len(person) < 1):
            logging.error('no face detedted for {}'.format(upload_file.name))
        else:
            logging.warn('too many faces detedted for {}'.format(upload_file.name))

def update(sess, header, person, idClass):
    if 'personId' in person.keys():
        person_id = person['personId']
        put_url = UPDATE_PEOPLE_URL.format(person_id)
        header.update({ 'Content-Type' : 'application/json' })
        logging.debug(header)
        with sess.put(put_url,  headers=header, data=json.dumps({"idClass" : "threat" })) as response:
            logging.info(response.status_code)
    else:
        logging.info('invalid person')

def process():
    params = {}
    session = requests.Session()
    df = pd.read_excel('data.xlsx', skiprows=0, usecols={0, 1, 2, 3, 4, 5}, encoding='latin-1')
    list = [tuple(x) for x in df.values]
    for a_name, a_person_type, a_external_id, a_age, a_gender, file_name in list:
        file_name = IMG_PATH.format(file_name)
        try:
            with open(file_name, 'rb') as upload_file:
                a_header = build_person(header = createHeader(user_id, passwd, directory), name = a_name, person_type = a_person_type, external_id = a_external_id, age = a_age, gender = a_gender)
                create_person(session, createHeader(user_id, passwd, directory), params, upload_file)
        except FileNotFoundError:
            logging.error('Missing file {}'.format(file_name))

if __name__ == '__main__':
    logging.info("Starting process...")
    start_time = datetime.now()
    try:
        process()
        end_time = datetime.now()
        elapsed_time = end_time - start_time
        logging.info('...ending process. Time slapsed {}'.format(elapsed_time))
    except Exception as e:
        logging.error('An error has ocurred. {}'.format(e))
