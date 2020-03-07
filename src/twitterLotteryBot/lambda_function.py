from requests_oauthlib import OAuth1Session, OAuth1
import requests
import json
import codecs
import time
import os
import datetime
import collections
import re
import random

OAUTH1 = os.environ['OAUTH1']
OAUTH2 = os.environ['OAUTH2']
OAUTH3 = os.environ['OAUTH3']
OAUTH4 = os.environ['OAUTH4']
SCREEN_NAME = os.environ['SCREEN_NAME']

def getOauth():
    return OAuth1(OAUTH1, OAUTH2, OAUTH3, OAUTH4)

def main():

    #botのツイートを取得
    doneList = requests.get(
        f'https://api.twitter.com/1.1/statuses/user_timeline.json?screen_name={SCREEN_NAME}&count=100',
        auth=getOauth()
    ).json()
    if "errors" in doneList:
        print(doneList)
        return
    doneList = list(map(lambda x:x["in_reply_to_status_id"],doneList))
    print(doneList)


    #指定タグのツイートを取得
    search = '%23抽選bot'
    response = requests.get(
        f'https://api.twitter.com/1.1/search/tweets.json?q={search}&count=10&lang=ja&result_type=mixed',
        auth=getOauth()
    ).json()

    if "errors" in response:
        print(response)
        return

    statusList = response["statuses"]

    for status in statusList:
        if "retweeted_status" in status:
            print("RT skip")
            continue
        if status["in_reply_to_status_id"]:
            print("rep skip")
            continue
            
        print(f"text:{status['text']}")
        tweet_id = status['id']
        print(f"tweet_id:{tweet_id}")
        print(f"user_id:{status['user']['id']}")
        print(f"user_screen_name:{status['user']['screen_name']}")
        print(status)
        sleepTime = random.random() * 20
        
        #指定タグのツイート者宛のリプライを取得
        search = f"%40{status['user']['screen_name']}"
        rep_response = requests.get(
            f'https://api.twitter.com/1.1/search/tweets.json?q={search}&count=10&lang=ja&result_type=mixed',
            auth=getOauth()
        ).json()
        
        if "errors" in rep_response:
            print(rep_response)
            continue
        
        rep_statusList = rep_response["statuses"]
        
        for rep_status in rep_statusList:
            if "retweeted_status" in status:
                print("RT skip")
                continue
            
            if rep_status['in_reply_to_status_id'] != tweet_id:
                continue

            if rep_status['id'] in doneList:
                print(f"{rep_status['user']['name']} reply done")
                continue

            print(f"text:{rep_status['text']}")
            print(f"tweet_id:{rep_status['id']}")
            print(f"user_id:{rep_status['user']['id']}")
            print(f"user_name:{rep_status['user']['name']}")

            #リプライする
            if random.random() <= 0.1:
                lot = "大吉"
            elif random.random() <= 0.6:
                lot = "中吉"
            else:
                lot = "小吉"
            message = f'{rep_status["user"]["name"]}さん、リプありがとうございます！\n「{lot}」が当選しました。だだいまテストツイート中です。\n\n※このツイートはbotからの自動送信です'
            in_reply_to_status_id = rep_status['id']
            print(f"message:{message} exec")
            print(f"in_reply_to_status_id:{in_reply_to_status_id} exec")
            replyResponse = requests.post(
                 f'https://api.twitter.com/1.1/statuses/update.json',
                 data={"status":message
                     ,"in_reply_to_status_id":in_reply_to_status_id
                     ,"auto_populate_reply_metadata":True},
             auth=getOauth()
            ).json()
            print(replyResponse)
        

def lambda_handler(event, context):

    try:
        main()

    except:
        import traceback
        traceback.print_exc()

