#!/usr/bin/python3

from datetime import datetime
import time
import logging
import numpy as np
import os
import cv2
import requests
import base64
import json
from PIL import Image, ImageEnhance

logging.basicConfig(filename='app.log', filemode='w',level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logging.getLogger().addHandler(logging.StreamHandler())

BASE_URL = 'https://covi.int2.real.com{0}'
user_id = 'realnetworksbra'
passwd = 'qaz123'
directory = 'test-align4'
site='test'
source = 'pythonBatch'

ORIGINAL_PATH = 'original/'
NEW_PATH_ALIGNED= 'aligned/'

UPDATE_PEOPLE_URL = BASE_URL.format("/people/{}")
PEOPLE_URL = BASE_URL.format("/people?")
PEOPLE_URL = PEOPLE_URL+"insert=true&insert-profile=true"
PEOPLE_URL = PEOPLE_URL+"&update=false&merge=false"
PEOPLE_URL = PEOPLE_URL+"&detect-age=false&detect-gender=false&detect-sentiment=false"
PEOPLE_URL = PEOPLE_URL+"&source=batchImport&site={0}&source={1}"

retry_files = []

def createHeader(user_id, password, directory):
    enconding = 'utf-8'
    encode_password =  base64.b64encode(bytes(password, enconding)).decode(enconding)
    header_auth = "{0}:{1}".format(user_id, encode_password)
    return {
        'Content-Type': 'application/octet-stream',
        'X-RPC-AUTHORIZATION' : header_auth,
        'X-RPC-DIRECTORY' : directory
    }

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
                logging.warning('Alpha channel detected. Removing it and creating new file with the content')
                new_file = upload_file+'.jpg'
                im.convert('RGB').save(new_file, 'JPEG')
                return new_file
    except IOError as e:
        raise Exception('Missing file {}. Thrown exception {}'.format(str(upload_file)), e)

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

def rotateImage(file_path, name, angle):
    image = cv2.imread(file_path, cv2.IMREAD_COLOR)
    (h, w) = image.shape[:2]
    center = (w / 2, h / 2)
    scale = 1.0
    M = cv2.getRotationMatrix2D(center, angle, scale)
    image = cv2.warpAffine(image, M, (h, w)) 
    new_file_path = NEW_PATH_ALIGNED + name +"_"+str(angle)+ ".jpg"
    cv2.imwrite(new_file_path, image)
    return new_file_path

def create_person(sess, header, params, upload_file):
    post_url = PEOPLE_URL.format(site, source)
    with sess.post(post_url,  headers=header, data=upload_file) as response:
        if response.status_code == requests.codes.created:
            person = response.json()['identifiedFaces']
            if (len(person) < 1):
                logging.error('no face detected for {}'.format(upload_file.name))
            elif (len(person) > 1):
                logging.error('too many faces detected for {}'.format(upload_file.name))
            elif 'personId' not in person[0].keys() and 'mediaId' in person[0].keys():
                logging.error('{} not registered. Face not detected. Check detected quality attributes: {}'.format(upload_file.name, get_quality_params(person[0])))
                return True #Not actually a correct response, but it´s not worth retrying
            elif 'personId' in person[0].keys() and 'newId' in person[0].keys() and person[0]['newId']==True:
                logging.info('Face detected for {}. registered. Person-Id {}'.format(upload_file.name, person[0]['personId']))
                return True
            elif 'personId' in person[0].keys() and 'newId' not in person[0].keys():
                logging.warning('Face detected for {}. Updated. Person-Id {}'.format(upload_file.name, person[0]['personId']))
                return True
        return False

def process(path):
    params = {}
    sess = requests.Session()

    files = []
    for r, d, f in os.walk(path):
        for file in f:
            if '.jpg' in file:
                full_path_of_file = os.path.join(r, file)
                files.append(full_path_of_file)

    for f in files:
        person_name = f.replace(path, '').split('-')[0]
        try:
            a_header = build_person(header = createHeader(user_id, passwd, directory), name = person_name)
            with open(f, 'rb') as data:
                if (create_person(sess, a_header, params, data) == False):
                    retry_files.append(f)
        except FileNotFoundError:
            logging.error('Missing file {}'.format(f))

    logging.info('Ended first step')
    logging.warning('{} file(s) for realignment. {}'.format(len(retry_files), retry_files))

    for f in retry_files:
        person_name = f.replace(path, '').split('-')[0]
        try:
            for angle in (90, 180, 270):
                file_name =  rotateImage(f, person_name, angle)
                if file_name == None:
                    logging.error('Not possible to realign {}'.format(f))
                else:
                    a_header = build_person(header = createHeader(user_id, passwd, directory), name = person_name)
                    with open(file_name, 'rb') as data:
                        if(create_person(sess, a_header, params, data)):
                            break
        except FileNotFoundError:
            logging.error('Missing file {}'.format(f))

if __name__ == '__main__':
    logging.info("Starting process...")
    start_time = datetime.now()
    try:
        process(ORIGINAL_PATH)
        end_time = datetime.now()
        elapsed_time = end_time - start_time
        logging.info('...ending process. Time slapsed {}'.format(elapsed_time))
    except Exception as e:
        logging.error('An error has ocurred. {}'.format(e))
