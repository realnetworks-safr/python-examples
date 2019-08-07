#!/usr/bin/python3
from PIL import Image, ImageEnhance
import requests
import base64
from datetime import datetime
import time
import logging
import json

logging.basicConfig(filename='app.log', filemode='w+',level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logging.getLogger().addHandler(logging.StreamHandler())

BASE_URL = 'https://covi.int2.real.com{0}'

UPDATE_PEOPLE_URL = BASE_URL.format("/people/{}")

PEOPLE_URL = BASE_URL.format("/people?")
PEOPLE_URL = PEOPLE_URL+"insert=true&insert-profile=true"
PEOPLE_URL = PEOPLE_URL+"&update=false&merge=false"
PEOPLE_URL = PEOPLE_URL+"&detect-age=false&detect-gender=false&detect-sentiment=false"
PEOPLE_URL = PEOPLE_URL+"&source=batchImport&site={0}&source={1}"
PEOPLE_URL = PEOPLE_URL+"&min-cpq=0.53"#

user_id = 'userid'
passwd = 'password'
directory = 'main'
site='test'
source = 'pythonBatch'

IMG_PATH = 'images/{0}'

def createHeader(user_id, password, directory):
    enconding = 'utf-8'
    encode_password =  base64.b64encode(bytes(password, enconding)).decode(enconding)
    header_auth = "{0}:{1}".format(user_id, encode_password)
    return {
        'Content-Type': 'application/octet-stream',
        'X-RPC-AUTHORIZATION' : header_auth,
        'X-RPC-DIRECTORY' : directory
    }

def build_person(header, name):
    a_header = {}
    a_header.update(header)
    if not isEmpty(name):
        a_header.update({
            'X-RPC-PERSON-NAME' : str(name)
        })
    return a_header

def isEmpty(field):
    return field is None or field == ''

def create_person(sess, header, params, upload_file):
    post_url = PEOPLE_URL.format(site, source)
    with sess.post(post_url,  headers=header, data=upload_file) as response:
        if response.status_code == requests.codes.created:
            person = response.json()['identifiedFaces']
            if (len(person) < 1):
                logging.error('no face detedted for {}'.format(upload_file.name))
            elif (len(person) > 1):
                logging.error('too many faces detedted for {}'.format(upload_file.name))
            if 'personId' not in person[0].keys() and 'mediaId' in person[0].keys():
                logging.error('not registered. Face not detected. Check detected quality attributes: {}'.format(get_quality_params(person[0])))
                return False
            if 'personId' in person[0].keys() and 'newId' in person[0].keys() and person[0]['newId']==True:
                logging.info('Face detected. registered. Person-Id {}'.format(person[0]['personId']))
                return True
            if 'personId' in person[0].keys() and 'newId' not in person[0].keys():
                logging.warn('Face detected. Updated. Person-Id {}'.format(person[0]['personId']))
                return False
        logging.error('Error received from SAFR: {}'.format(response.status_code))
        return False

def get_quality_params(personObj):
    response = {}
    attributes = personObj['attributes']
    if 'centerPoseQuality' in attributes.keys():
        response.update({'centerPoseQuality' : attributes['centerPoseQuality']})
    if 'sharpnessQuality' in attributes.keys():
        response.update({'sharpnessQuality' : attributes['sharpnessQuality']})
    if 'contrastQuality' in attributes.keys():
        response.update({'contrastQuality' : attributes['contrastQuality']})
    return response

def remove_alpha(upload_file):
    try:
        with Image.open(upload_file) as im:
            if(im.mode == 'RGBA'):
                logging.warn('Alpha channel detected. Removing it and creating new file with the content')
                new_file = upload_file+'.jpg'
                im.convert('RGB').save(new_file, 'JPEG')
                return new_file
            else:
                logging.info('No alpha channel detected')
                return upload_file
    except IOError as e:
        raise Exception('Missing file {}'.format(str(upload_file)))

def process():
    params = {}
    sess = requests.Session()
    file_name = IMG_PATH.format('face_2.png')
    try:
        file_name = remove_alpha(file_name)
        a_header = build_person(header = createHeader(user_id, passwd, directory), name = 'alpha channel off')
        with open(file_name, 'rb') as data:
            create_person(sess, a_header, params, data)            
    except FileNotFoundError:
        logging.error('Missing file {}'.format(file_name))
        
if __name__ == '__main__':
    logging.info("Starting process...")
    start_time = datetime.now()
    try:
        process()
        logging.info('...ending process. Time slapsed {}'.format(datetime.now() - start_time))
    except Exception as e:
        logging.error('An error has ocurred. {}'.format(e))