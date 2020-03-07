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
import boto3

OAUTH1 = os.environ['OAUTH1']
OAUTH2 = os.environ['OAUTH2']
OAUTH3 = os.environ['OAUTH3']
OAUTH4 = os.environ['OAUTH4']
SCREEN_NAME = os.environ['SCREEN_NAME']


def getOauth():
    return OAuth1(OAUTH1, OAUTH2, OAUTH3, OAUTH4)


def getParam(key):
    dynamoDB = boto3.resource("dynamodb")
    paramTable = dynamoDB.Table("twitterLotPram")
    item = paramTable.get_item(Key={"key": key})
    if "Item" in item:
        return item["Item"]
    else:
        return []


def putParam(key, data):
    dynamoDB = boto3.resource("dynamodb")
    paramTable = dynamoDB.Table("twitterLotPram")
    paramTable.put_item(Item={"key": key, "data": data})


def getItem(key):
    dynamoDB = boto3.resource("dynamodb")
    table = dynamoDB.Table("twitterLotterBot")
    item = table.get_item(Key=key)
    if "Item" in item:
        return item["Item"]
    else:
        return None


def putItem(data):
    dynamoDB = boto3.resource("dynamodb")
    table = dynamoDB.Table("twitterLotterBot")
    table.put_item(Item=data)


def main():

    dynamoDB = boto3.resource("dynamodb")
    table = dynamoDB.Table("twitterLotterBot")

    # botのツイートを取得
    doneList = requests.get(
        f'https://api.twitter.com/1.1/statuses/user_timeline.json?screen_name={SCREEN_NAME}&count=10',
        auth=getOauth()
    ).json()
    if "errors" in doneList:
        print(doneList)
        return
    doneList = getParam("doneList") + \
        list(map(lambda x: x["in_reply_to_status_id"], doneList))
    doneList = list(set(doneList))
    putParam("doneList", doneList)
    print(doneList)

    # 指定タグのツイートを取得
    search = '%23抽選bot'
    response = requests.get(
        f'https://api.twitter.com/1.1/search/tweets.json?q={search}&count=50&lang=ja&result_type=mixed&tweet_mode=extended',
        auth=getOauth()
    ).json()

    if "errors" in response:
        print(response)
        return

    statusList = response["statuses"]

    tweetList = getParam("tweetList") + \
        list(map(lambda x: x["statuses"]['id'], response))
    tweetList = list(set(tweetList))
    putParam("tweetList", tweetList)

    for status in statusList:

        if "retweeted_status" in status:
            print("RT skip")
            continue
        if status["in_reply_to_status_id"]:
            print("rep skip")
            continue

        data = {"statusId": status['id']}
        data = getItem(data)

        tweet_id = status['id']
        main_text = status['full_text']

        if "…" in main_text:
            tmp = requests.get(
                f'https://api.twitter.com/1.1/statuses/show.json?id={tweet_id}&tweet_mode=extended',
                auth=getOauth()
            ).json()
            main_text = tmp['full_text']

        data["text"] = main_text
        data["user_id"] = status['user']['id']
        data["user_screen_name"] = status['user']['screen_name']

        lot_pro = re.findall(r'(\[.+?\]\(\d+)', main_text)
        lot_pro = list(map(lambda x: {"name": re.findall(
            r'\[(.+)\]', x)[0], "pro": int(re.findall(r'(\d+)', x)[0])}, lot_pro))
        data["lot_pro"] = lot_pro

        lot_message = ""
        for p in lot_pro:
            lot_message += f'{p["name"]}:{p["pro"]}%,'
        data["lot_message"] = lot_message

        if tweet_id not in doneList:
            print(f"{tweet_id} first reply exec")

            # リプライする
            if len(lot_pro) == 0:
                message = f'#抽選bot のご利用ありがとうございます！\n申し訳ありませんが、確立を読み取れませんでした。\n正しい使い方などは↓のリンクをご覧ください。\nhttps://encr.jp/blog/posts/20200306_morning/\n\n※このツイートはbotからの自動送信です'
            else:
                message = f'#抽選bot のご利用ありがとうございます！\n{lot_message[:-1]}で抽選いたします。\nhttps://encr.jp/blog/posts/20200306_morning/\n\n※このツイートはbotからの自動送信です'
            data["main_reply_message"] = message
            in_reply_to_status_id = tweet_id
            replyResponse = requests.post(
                f'https://api.twitter.com/1.1/statuses/update.json',
                data={"status": message, "in_reply_to_status_id": in_reply_to_status_id,
                      "auto_populate_reply_metadata": True},
                auth=getOauth()
            ).json()

            if "errors" in replyResponse:
                print(replyResponse)
                return

        if len(lot_pro) == 0:
            putItem(data)
            continue

        sleepTime = random.random() * 20
        time.sleep(sleepTime)

        # 指定タグのツイート者宛のリプライを取得
        search = f"%40{status['user']['screen_name']}"
        repResponse = requests.get(
            f'https://api.twitter.com/1.1/search/tweets.json?q={search}&count=10&lang=ja&result_type=mixed',
            auth=getOauth()
        ).json()

        if "errors" in repResponse:
            print(repResponse)
            continue

        repStatusList = repResponse["statuses"]

        for rep_status in repStatusList:
            if "retweeted_status" in status:
                print("RT skip")
                continue

            if rep_status['in_reply_to_status_id'] != tweet_id:
                continue

            if rep_status['id'] in doneList or rep_status['user']['screen_name'] == SCREEN_NAME:
                print(f"{rep_status['user']['name']} reply done")
                continue

            print(f"text:{rep_status['text']}")
            print(f"tweet_id:{rep_status['id']}")
            print(f"user_id:{rep_status['user']['id']}")
            print(f"user_screen_name:{rep_status['user']['screen_name']}")
            print(f"user_name:{rep_status['user']['name']}")

            # 抽選する
            sump = 0
            yourp = random.random() * 100
            lot = None
            for p in lot_pro:
                sump += p["pro"]
                if yourp <= sump:
                    lot = p["name"]
                    break

            # リプライする
            if lot is not None:
                message = f'{rep_status["user"]["name"]}さん、リプありがとうございます！\n「{lot}」が当選しました。\n\n※このツイートはbotからの自動送信です #抽選bot'
            else:
                message = f'{rep_status["user"]["name"]}さん、リプありがとうございます！\n残念ながら、今回は落選してしまいました…\n\n※このツイートはbotからの自動送信です #抽選bot'

            in_reply_to_status_id = rep_status['id']
            print(f"message:{message} exec")
            print(f"in_reply_to_status_id:{in_reply_to_status_id} exec")
            replyResponse = requests.post(
                f'https://api.twitter.com/1.1/statuses/update.json',
                data={"status": message, "in_reply_to_status_id": in_reply_to_status_id,
                      "auto_populate_reply_metadata": True},
                auth=getOauth()
            ).json()
            print(replyResponse)
        putItem(data)


def lambda_handler(event, context):

    try:
        main()

    except:
        import traceback
        traceback.print_exc()
