import json
import boto3
import re
import os
import datetime
import urllib.request
import traceback
from requests_oauthlib import OAuth1Session, OAuth1

OAUTH1 = os.environ['OAUTH1']
OAUTH2 = os.environ['OAUTH2']
OAUTH3 = os.environ['OAUTH3']
OAUTH4 = os.environ['OAUTH4']
SCREEN_NAME = os.environ['SCREEN_NAME']
TWITTER_BUKET = os.environ['TWITTER_BUKET']

def getOauth():
    return OAuth1(OAUTH1, OAUTH2, OAUTH3, OAUTH4)
