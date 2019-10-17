## Description
Sometimes while running batch registration to the SAFR plataform, some of the pictures, 
even thou they have good enough quality they can´t be recognized by SAFR because they´re rotated the wrong way. This script tries
to solve this by first running the whole batch of pictures and if any of those pictures return as face not detected, they´ll be
retried later by rotating the pictures 90, 180 and then 270 degrees.

## Please be advised, source folder and folder for files to be aligned must be defined and created before running the script.

## Install dependencies
Run pip install -r requirements --upgrade --user

#modify app.py with the correct values
BASE_URL = 'https://covi.int2.real.com{0}'
user_id = 'userid'
passwd = 'pwd'
directory = 'test-align4'
site='test'
source = 'pythonBatch'
ORIGINAL_PATH = 'original/'
NEW_PATH_ALIGNED= 'aligned/'

#Run with Python3
./app.py
python app.py
