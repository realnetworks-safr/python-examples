#!/usr/bin/python3

from datetime import datetime
import os
import shutil

import logging
import base64
import requests
import json

import cv2 as cv
from PIL import Image, ImageEnhance

import pandas as pd
import numpy as np
import math

logging.basicConfig(filename='app.log', filemode='w',level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logging.getLogger().addHandler(logging.StreamHandler())

#change required
user_id = 'userid'
passwd = 'passwd'
BASE_URL = 'https://covi.int2.real.com{0}'
#change optional
DIRECTORY = 'python-test'
SITE='python-test'
SOURCE = 'python-test'
#folders - change only if necessary
SOURCE_PATH = 'source/'
NOK_PATH = 'nok/'
OK_PATH= 'ok/'
#Default values
DEFAULT_MIN_CENTER_POSE_QUALITY = 0.76 
DEFAULT_MIN_SHARPNESS =  0.62
DEFAULT_MIN_CONTRAST =  0.63
DEFAULT_MIN_FACE_WIDTH = 210
DEFAULT_MIN_FACE_HEIGHT = 260

URL_RECOGNITION = BASE_URL.format('/people?')
#disabled registering/updating, only recogintion is used
URL_RECOGNITION = URL_RECOGNITION + 'insert=false&update=false&merge=false&regroup=false&insert-profile=false'
URL_RECOGNITION = URL_RECOGNITION + '&provide-face-id=false&differentiate=false'
#disabled detectors, decrease memory/cpu usage
URL_RECOGNITION = URL_RECOGNITION + '&detect-age=false&detect-gender=false&detect-sentiment=false'
URL_RECOGNITION = URL_RECOGNITION + '&detect-occlusion=true&min-size=0'
#disabled filter, allow anything
URL_RECOGNITION = URL_RECOGNITION + '&min-cpq=0&min-fsq=0&min-fcq=0&max-occlusion=0&type=person&include-expired=false'
URL_RECOGNITION = URL_RECOGNITION + '&site={}&source={}'.format(SITE, SOURCE)

count_success = 0
count_errors = 0
total = 0

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

def get_dimension(personObj):
    response = {}
    attributes = personObj['attributes']
    if 'dimension' in attributes.keys():
        dimension = attributes['dimension']
        response.update( {'height' : dimension['height']} )
        response.update( {'width' : dimension['width']} )
    return response

def get_image_points(points):
    #2D image points. If you change the image, you need to change vector
	return np.array([
        (points['nose-tip-x'], points['nose-tip-y']),     # Nose tip
	    (399, 561),     # Chin
	    (points['left-eye-center-x'], points['left-eye-center-y']),     # Left eye left corner
	    (points['right-eye-center-x'], points['right-eye-center-y']),     # Right eye right corne
	    (points['left-mouth-corner-x'], points['left-mouth-corner-y']),     # Left Mouth corner
	    (points['right-mouth-corner-x'], points['right-mouth-corner-y'])      # Right mouth corner
    ], dtype="double")

def get_model_points():
    # 3D model points.
    return np.array([
        (0.0, 0.0, 0.0),             # Nose tip
        (0.0, -330.0, -65.0),        # Chin
        (-225.0, 170.0, -135.0),     # Left eye left corner
        (225.0, 170.0, -135.0),      # Right eye right corne
        (-150.0, -150.0, -125.0),    # Left Mouth corner
        (150.0, -150.0, -125.0)      # Right mouth corner
    ])

def get_attributes(personObj):
    response = {}
    attributes = personObj['attributes']
    response.update( {'occlusion' : None} )
    if 'landmarks' in attributes.keys():
        logging.debug('attributes {}'.format(attributes))
        attributes = attributes['landmarks']
        logging.debug('attributes {}'.format(attributes))
        if 'right-eye-center' in attributes.keys():
            attr = attributes['right-eye-center']
            response.update( {'right-eye-center-x' : attr['x']} )
            response.update( {'right-eye-center-y' : attr['y']} )
        if 'left-eye-center' in attributes.keys():
            attr = attributes['left-eye-center']
            response.update( {'left-eye-center-x' : attr['x']} )
            response.update( {'left-eye-center-y' : attr['y']} )
        if 'nose-tip' in attributes.keys():
            attr = attributes['nose-tip']
            response.update( {'nose-tip-x' : attr['x']} )
            response.update( {'nose-tip-y' : attr['y']} )
        if 'right-mouth-corner' in attributes.keys():
            attr = attributes['right-mouth-corner']
            response.update( {'right-mouth-corner-x' : attr['x']} )
            response.update( {'right-mouth-corner-y' : attr['y']} )
        if 'left-mouth-corner' in attributes.keys():
            attr = attributes['left-mouth-corner']
            response.update( {'left-mouth-corner-x' : attr['x']} )
            response.update( {'left-mouth-corner-y' : attr['y']} )
    if 'occlusion' in attributes.keys():        
        response.update( {'occlusion' : attributes['occlusion']} )
    return response

def get_roll_pitch_yaw(model_points, image_points, size):
    focal_length = size[1]
    center = (size[1]/2, size[0]/2)
    camera_matrix = np.array(
        [[focal_length, 0, center[0]],
        [0, focal_length, center[1]],
        [0, 0, 1]], dtype = "double")
    axis = np.float32([[500,0,0], 
                          [0,500,0], 
                          [0,0,500]])

    dist_coeffs = np.zeros((4,1)) # Assuming no lens distortion
    (success, rotation_vector, translation_vector) = cv.solvePnP(model_points, image_points, camera_matrix, dist_coeffs, cv.SOLVEPNP_ITERATIVE)

    imgpts, jac = cv.projectPoints(axis, rotation_vector, translation_vector, camera_matrix, dist_coeffs)
    modelpts, jac2 = cv.projectPoints(model_points, rotation_vector, translation_vector, camera_matrix, dist_coeffs)
    rvec_matrix = cv.Rodrigues(rotation_vector)[0]
    proj_matrix = np.hstack((rvec_matrix, translation_vector))
    eulerAngles = cv.decomposeProjectionMatrix(proj_matrix)[6]
    (pitch, yaw, roll) = [math.radians(_) for _ in eulerAngles]
    pitch = math.degrees(math.asin(math.sin(pitch)))
    roll = -math.degrees(math.asin(math.sin(roll)))
    yaw = math.degrees(math.asin(math.sin(yaw)))

    return (pitch, yaw, roll)

def submit_photo(sess, header, relative_file_path):
    global count_errors
    try:
        with open(relative_file_path, 'rb') as upload_file:
            with sess.post(URL_RECOGNITION.format(SITE, SOURCE),  headers=header, data=upload_file) as response:
                if response.status_code == 401:
                    raise Exception('Could not connect, check the credentials: {}:{} and the URL: {}'.format(user_id, passwd, URL_RECOGNITION))
                if response.status_code == requests.codes.created:
                    logging.debug('response {}'.format(response))
                    response = response.json()['identifiedFaces']
                    logging.debug('json object body {}'.format(response))
                    if (bool(response) and len(response) != 0):
                        response = response[0]
                    if (len(response) == 0): #nothing has been detected from the file
                        count_errors = count_errors +1

                        logging.error('No face has been detected for file {} is invalid. as JSON object {}. Moving file to {}'
                        .format(relative_file_path, response, NOK_PATH))
                        move_file(relative_file_path, NOK_PATH)
                    return response
    except FileNotFoundError:
        logging.error('Missing file {}'.format(relative_file_path))
    return None

def move_file(target_file, new_path):
    #create folder if it does not exist
    if not os.path.exists(new_path):
        os.mkdir(new_path)
    moved_path = os.path.realpath(target_file)
    new_file_path = os.path.realpath(target_file).replace(SOURCE_PATH, new_path)
    shutil.move(moved_path, new_file_path)

def verify_params(relative_file_path, dimension, quality_params, occlusion):
    global count_success
    global count_errors

    center_pose_quality = quality_params['centerPoseQuality']
    sharpness = quality_params['sharpnessQuality']
    contrast = quality_params['contrastQuality']
    face_width= dimension['width']
    face_height = dimension['height']

    if (center_pose_quality < DEFAULT_MIN_CENTER_POSE_QUALITY or sharpness < DEFAULT_MIN_SHARPNESS or contrast < DEFAULT_MIN_CONTRAST 
    or  face_width < DEFAULT_MIN_FACE_WIDTH or face_height < DEFAULT_MIN_FACE_HEIGHT):
        #move to NOK folder
        count_errors = count_errors +1
        move_file(relative_file_path, NOK_PATH)
        logging.info('File: {} is  {}. Moving to {} folder. dimension: {}, quality_params{}, occlusion: {}'.format(relative_file_path, 'Not Ok', NOK_PATH, dimension, quality_params, occlusion))
        return 'NOK'
    
    #move to OK folder    
    count_success = count_success +1
    move_file(relative_file_path, OK_PATH)
    logging.info('File: {} is  {}. Moving to {} folder.'.format(relative_file_path, 'Ok', OK_PATH))
    return 'OK'

def process(path):
    global total

    list_sources = []
    list_face_height = []
    list_face_width = []
    list_rolls = []
    list_pitchs = []
    list_yaws = []
    list_quality_params_sharpness = []
    list_quality_params_contrast = []
    list_quality_params_center_pose_quality = []
    list_status = []
    list_occlusion = []

    a_session = requests.Session()
    a_header = createHeader(user_id, passwd, DIRECTORY)

    cont = 0
    for r, d, f in os.walk(path):        
        for file_item in f:            
            num_files = len(f)
            if '.jpg' in file_item.lower():
                cont = cont + 1
                relative_file_path = os.path.join(r, file_item)
                
                logging.info('Validating file: {} -  {}/{}'.format(relative_file_path, cont, num_files))

                im = cv.imread(relative_file_path)
                size = im.shape
                logging.debug('Size {}'.format(str(size)))

                dimension = {}
                attributes = {}
                quality_params = {}
                pitch = {}
                yaw = {}
                roll = {}
                occlusion = {}

                person_obj = submit_photo(a_session, a_header, relative_file_path)
                logging.debug('Person as JSON object {}'.format(person_obj))

                if (bool(person_obj)):
                    dimension = get_dimension(person_obj)
                    attributes = get_attributes(person_obj)
                    quality_params = get_quality_params(person_obj)                    

                    image_points = get_image_points(attributes)
                    model_points = get_model_points()
                    occlusion = attributes['occlusion']

                    (pitch, yaw, roll) = get_roll_pitch_yaw(model_points, image_points, size)

                    is_ok = verify_params(relative_file_path, dimension, quality_params, occlusion)
                    list_occlusion.append(occlusion)
                    list_sources.append(relative_file_path)
                    list_face_height.append(dimension['height'])
                    list_face_width.append(dimension['width'])
                    list_rolls.append(roll)
                    list_pitchs.append(pitch)
                    list_yaws.append(yaw)
                    list_quality_params_sharpness.append(quality_params['sharpnessQuality'])
                    list_quality_params_contrast.append(quality_params['contrastQuality'])
                    list_quality_params_center_pose_quality.append(quality_params['centerPoseQuality'])
                    list_status.append(is_ok)

                    logging.debug('attributes: {}'.format(str(attributes)))
                    logging.debug('image_points: {}'.format(str(image_points)))
                    logging.debug('model_points: {}'.format(str(model_points)))
                else:
                    list_sources.append(relative_file_path)
                    list_face_height.append(None)
                    list_face_width.append(None)
                    list_rolls.append(None)
                    list_pitchs.append(None)
                    list_yaws.append(None)
                    list_quality_params_sharpness.append(None)
                    list_quality_params_contrast.append(None)
                    list_quality_params_center_pose_quality.append(None)
                    list_status.append("NOK")
                    list_occlusion.append(None)

                TEMPLATE_MSG = 'Image: {} \n Size: {} \n Roll {} \n Pitch:: {} \n Yaw: {} \n Quality Params: {} \n Occlusion: {} \n\n '
                logging.debug(TEMPLATE_MSG.format(relative_file_path, dimension, pitch, roll, yaw, quality_params, occlusion))

                df = pd.DataFrame({
                    'Source':list_sources, 
                    'Status':list_status,
                    'Height':list_face_height, 
                    'Width':list_face_width, 
                    'Roll':list_rolls, 
                    'Pitch':list_pitchs,
                    'Yaw':list_yaws,
                    'Sharpness':list_quality_params_sharpness,
                    'Contrast':list_quality_params_contrast,
                    'Center Pose Quality':list_quality_params_center_pose_quality,
                    'Occlusion':list_occlusion
                })                
                df.to_csv('result.csv', encoding='utf-8', index=False, sep=";")

    total = cont


if __name__ == '__main__':
    logging.info("Starting process...")
    start_time = datetime.now()
    try:
        process(SOURCE_PATH)        
    except Exception as e:
        logging.error('An error has ocurred. \n {}'.format(e))
    finally:
        logging.info('...ending process. Time slapsed {}. Success: {}, Errors: {}, Total: {}.'.format((datetime.now() - start_time), count_success, count_errors, total))
