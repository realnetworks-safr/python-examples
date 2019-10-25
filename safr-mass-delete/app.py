#!/usr/bin/python3
import requests
import base64
import pandas as pd
from datetime import datetime
import logging
from concurrent.futures import ThreadPoolExecutor
import threading

logging.basicConfig(filename='app.log', filemode='w',level=logging.DEBUG, format='"%(asctime)s"; "%(levelname)s"; "%(message)s"') ## CSV Style, ; instead of comma thou
logging.getLogger().addHandler(logging.StreamHandler())

executor = ThreadPoolExecutor(max_workers=10)

BASE_INT2_URL='https://covi.int2.real.com'
BASE_PROD_URL='https://covi.real.com'
IS_CUSTOM_INSTALL = False

KEY_HEADER_AUTHORIZATION='X-RPC-AUTHORIZATION'
KEY_HEADER_DIRECTORY='X-RPC-DIRECTORY'
FIND_RESOURCE='{0}/rootpeople/{1}'
DELETE_RESOURCE='{0}/people/{1}'

session = requests.Session()

def createHeader(user_id, password, directory):
    encode_password =  base64.b64encode(bytes(password, 'utf-8')).decode('utf-8')
    return {
        KEY_HEADER_AUTHORIZATION : user_id+':'+encode_password,
        KEY_HEADER_DIRECTORY : directory
    }

header = createHeader('userId', 'passwd', 'directory')

def findPeople():
    url = FIND_RESOURCE.format(BASE_INT2_URL,'?count=0&include-expired=true')
    response = session.get(url,  headers=header)
    response = response.json()["people"]
    return response

def deletePeople(person_id):
    params = {}
    url = DELETE_RESOURCE.format(BASE_INT2_URL,person_id)
    print(url)
    response = session.delete(url,  headers=header, data = params)
    if response is not None and data.status_code == 204:
        logging.info('Successfully deleted person-id {}'.format(person_id))
    else:
        logging.error('Error deleting person-id {}'.format(person_id))

def main():
    print("Starting process...")
    listPeople = [] 
    for person in findPeople():
        listPeople.append(person.get('personId'))
    for personId in listPeople:
        executor.submit(deletePeople, personId)

if __name__ == '__main__':
    main()
