#!/usr/bin/python3
import pandas as pd
import numpy as np
import requests
import base64
from datetime import datetime
import logging
from concurrent.futures import ThreadPoolExecutor
import threading

logging.basicConfig(filename='app.log', filemode='w',level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logging.getLogger().addHandler(logging.StreamHandler())

executor = ThreadPoolExecutor(max_workers=10)

BASE_URL = 'https://covi.int2.real.com{0}'
PEOPLE_URL = BASE_URL.format("/people?insert=true&update=false&merge=false")
PEOPLE_URL = PEOPLE_URL+"&detect-age=false&detect-gender=false&detect-sentiment=false"
PEOPLE_URL = PEOPLE_URL+"&source=batchImport&site={0}&source={1}"

KEY_HEADER_AUTHORIZATION='X-RPC-AUTHORIZATION'
KEY_HEADER_DIRECTORY='X-RPC-DIRECTORY'
IMG_PATH = 'images/{0}'

user_id = 'userid'
passwd = 'password'
directory = 'main'
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

def create_person(session, header, params, upload_file):
    post_url = PEOPLE_URL.format(site, source)
    response = session.post(post_url,  headers=header, data=upload_file.read(), stream=True)
    logging.debug(response)
    return response

def main():
    header = createHeader(user_id, passwd, directory)
    params = {}
    session = requests.Session()
    df = pd.read_excel('data.xlsx', skiprows=0, usecols={0, 1, 2, 3, 4, 5}, encoding='latin-1')
    list = [tuple(x) for x in df.values]
    for a_name, a_person_type, a_external_id, a_age, a_gender, file_name in list:
        file_name = IMG_PATH.format(file_name)
        try:
            with open(file_name, 'rb') as upload_file:
                a_header = build_person(header = header, name = a_name, person_type = a_person_type, external_id = a_external_id, age = a_age, gender = a_gender)
                executor.submit(create_person, session, a_header, params, upload_file)
        except FileNotFoundError as e:
            logging.error('Missing file {}'.format(upload_file.name))

if __name__ == '__main__':
    main()
