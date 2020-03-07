from requests_oauthlib import OAuth1Session, OAuth1
import requests
import json
import codecs
import time
from common import *
import random

def main():

    now = getNow()
    hour = now.hour
    getCount = 0
    if hour in [7,8]:
        getCount = 70
    elif hour in [11,17,20]:
        getCount = 100
    elif hour in [18,19]:
        getCount = 130
    elif hour in [6,12,21,22,23]:
        getCount = 50

    search = '%23駆け出しエンジニアと繋がりたい'
    print(f"search : {search}")
    print(f"getCount : {getCount}")
    response = requests.get(
        f'https://api.twitter.com/1.1/search/tweets.json?q={search}&count={getCount}&lang=ja&result_type=mixed',
        auth=getOauth()
    ).json()

    if "errors" in response:
        print(response)
        return

    statusList = response["statuses"]
    print(response["search_metadata"]["next_results"])
    print(len(statusList))

    oauth = getOauth()
    for user in statusList:
        print(f"{user['user']['id']}")
        sleepTime = random.random() * 20
        print(sleepTime)
        time.sleep(sleepTime)

        print(f"{user['user']['id']} favorites/create")
        tmpJson = requests.post(
            f'https://api.twitter.com/1.1/favorites/create.json',
            data={"id":user['id']},
            auth=oauth
        ).json()
        if "errors" in tmpJson:
            print(tmpJson)
            if tmpJson["errors"][0]["code"] != 139:
                return
        
    return 0

def lambda_handler(event, context):

    try:
        print(f"start: {getNow()}")
        res = main()
        print(f"end: {getNow()}")
        line.message(f"destroy:end")
        return res

    except:
        import traceback
        traceback.print_exc()


if __name__ == '__main__':

    print(f"start: {getNow()}")
    res = main()
    print(f"end: {getNow()}")
