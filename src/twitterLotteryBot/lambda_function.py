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
DEBUG_MODE = False

def getOauth():
    return OAuth1(OAUTH1, OAUTH2, OAUTH3, OAUTH4)


def getParam(key):
    dynamoDB = boto3.resource("dynamodb")
    paramTable = dynamoDB.Table("twitterLotPram")
    item = paramTable.get_item(Key={"key": key})
    if "Item" in item:
        return item["Item"]["data"]
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
        return key


def putItem(data):
    print(f"putItem:{data}")
    dynamoDB = boto3.resource("dynamodb")
    table = dynamoDB.Table("twitterLotterBot")
    table.put_item(Item=data)


def main():

    if DEBUG_MODE:
        print(f"★★★debugモード★★★")

    dynamoDB = boto3.resource("dynamodb")
    table = dynamoDB.Table("twitterLotterBot")

    # botのツイートを取得
    doneList = requests.get(
        f'https://api.twitter.com/1.1/statuses/user_timeline.json?screen_name={SCREEN_NAME}&count=50',
        auth=getOauth()
    ).json()
    if "errors" in doneList:
        print(doneList)
        return
    doneList = list(map(lambda x: x["in_reply_to_status_id_str"], doneList))
    doneList = list(set(getParam("doneList") + doneList))
    putParam("doneList", doneList)
    print(doneList)

    # 指定タグのツイートを取得
    search = '%23抽選bot'
    response = requests.get(
        f'https://api.twitter.com/1.1/search/tweets.json?q={search}&count=100&lang=ja&result_type=mixed&tweet_mode=extended',
        auth=getOauth()
    ).json()

    if "errors" in response:
        print(response)
        return

    # if DEBUG_MODE:
    #     print(response)

    statusList = response["statuses"]

    tweetList = getParam("tweetList")

    retweetedList = list(filter(lambda x:"retweeted_status" in x,statusList))
    quotedList = list(filter(lambda x:"quoted_status_id_str" in x,statusList))

    # if DEBUG_MODE:
    #     print(f"retweetedList:{retweetedList}")
    #     print(f"quotedList:{quotedList}")

    for status in statusList:

        if "retweeted_status" in status:
            print("RT skip")
            continue
        if status["in_reply_to_status_id_str"]:
            print("rep skip")
            continue
        if "quoted_status_id_str" in status:
            print("引用RT skip")
            continue

        tweet_id = status['id_str']
        data = {"statusId": tweet_id}
        data = getItem(data)

        main_text = status['full_text']

        if "…" in main_text:
            tmp = requests.get(
                f'https://api.twitter.com/1.1/statuses/show.json?id={tweet_id}&tweet_mode=extended',
                auth=getOauth()
            ).json()
            main_text = tmp['full_text']

        data["text"] = main_text
        data["user_id"] = status['user']['id_str']
        data["user_screen_name"] = status['user']['screen_name']

        # 抽選内容取得
        lot_pro = re.findall(r'(\[.+?\]\(\d+)', main_text)
        lot_pro = list(map(lambda x: {"name": re.findall(
            r'\[(.+)\]', x)[0], "pro": int(re.findall(r'\((\d+)', x)[0])}, lot_pro))

        lot_message = ""
        for p in lot_pro:
            lot_message += f'{p["name"]}:{p["pro"]}%,'

        #未リプライの募集ツイートのみ処理する
        if tweet_id not in doneList:
            print(f"{tweet_id} first reply exec")

            #リプライメッセージ作成
            if "lot_pro" not in data:
                if len(lot_pro) == 0:
                    message = f'#抽選bot のご利用ありがとうございます！\n申し訳ありませんが、確立を読み取れませんでした。\n正しい使い方などは↓のリンクをご覧ください。\nhttps://encr.jp/blog/posts/20200306_morning/\n\n※このツイートはbotからの自動送信です'
                else:
                    data["lot_pro"] = lot_pro
                    data["lot_message"] = lot_message
                    message = f'#抽選bot のご利用ありがとうございます！\n{lot_message[:-1]}で抽選いたします。\nhttps://encr.jp/blog/posts/20200306_morning/\n\n※このツイートはbotからの自動送信です'
                data["main_reply_message"] = message

            # リプライする
            print(f'★★★{data["main_reply_message"]}を送信★★★')
            if not DEBUG_MODE:
                in_reply_to_status_id = tweet_id
                replyResponse = requests.post(
                    f'https://api.twitter.com/1.1/statuses/update.json',
                    data={"status": data["main_reply_message"], "in_reply_to_status_id": int(in_reply_to_status_id),
                          "auto_populate_reply_metadata": True},
                    auth=getOauth()
                ).json()
    
                if "errors" in replyResponse:
                    print(replyResponse)
                    return
            
            putItem(data)
            doneList += [in_reply_to_status_id]
            tweetList += [in_reply_to_status_id]


        if len(lot_pro) == 0:
            continue

    print(f"tweetList:{tweetList}")
    for tweet_id in tweetList:
        status = getItem({"statusId": tweet_id})
        print(f'★★★{status["text"]}に対して処理開始★★★')
        if len(status["lot_pro"]) == 0:
            continue
        sleepTime = random.random() * 20
        time.sleep(sleepTime)

        # 指定タグのツイート者宛のリプライを取得
        search = f"%40{status['user_screen_name']}"
        repResponse = requests.get(
            f'https://api.twitter.com/1.1/search/tweets.json?q={search}&count=100&lang=ja&result_type=mixed',
            auth=getOauth()
        ).json()

        if "errors" in repResponse:
            print(repResponse)
            continue

        repStatusList = repResponse["statuses"]

        print("★reply★")
        for rep_status in repStatusList:
            if "retweeted_status" in status:
                print("RT skip")
                continue

            if rep_status['in_reply_to_status_id_str'] != tweet_id:
                continue

            if rep_status['id_str'] in doneList or rep_status['user']['screen_name'] == SCREEN_NAME:
                print(f"{rep_status['user']['name']} reply done")
                continue

            print(f"text:{rep_status['text']}")
            print(f"tweet_id:{rep_status['id_str']}")
            print(f"user_id:{rep_status['user']['id_str']}")
            print(f"user_screen_name:{rep_status['user']['screen_name']}")
            print(f"user_name:{rep_status['user']['name']}")

            # 抽選する
            sump = 0
            yourp = random.random() * 100
            print(f"抽選値：{yourp}")
            lot = None
            for p in status["lot_pro"]:
                sump += int(p["pro"])
                if yourp <= sump:
                    lot = p["name"]
                    break

            # リプライメッセージ作成
            if lot is not None:
                message = f'{rep_status["user"]["name"]}さん、リプありがとうございます！\n「{lot}」が当選しました。\n\n※このツイートはbotからの自動送信です #抽選bot'
            else:
                message = f'{rep_status["user"]["name"]}さん、リプありがとうございます！\n残念ながら、今回は落選してしまいました…\n\n※このツイートはbotからの自動送信です #抽選bot'

            # リプライする
            print(f"★★★{message}を送信★★★")
            if not DEBUG_MODE:
                in_reply_to_status_id = rep_status['id_str']
                replyResponse = requests.post(
                    f'https://api.twitter.com/1.1/statuses/update.json',
                    data={"status": message, "in_reply_to_status_id": in_reply_to_status_id,
                          "auto_populate_reply_metadata": True},
                    auth=getOauth()
                ).json()
                print(replyResponse)
                doneList += [in_reply_to_status_id]
            print(f"exec")

        # print("★quoted★")
        # for rep_status in quotedList:
            
        #     if rep_status['quoted_status_id_str'] != tweet_id:
        #         continue

        #     if rep_status['id_str'] in doneList or rep_status['user']['screen_name'] == SCREEN_NAME:
        #         print(f"{rep_status['user']['name']} reply done")
        #         continue

        #     print(f"text:{rep_status['full_text']}")
        #     print(f"tweet_id:{rep_status['id_str']}")
        #     print(f"user_id:{rep_status['user']['id_str']}")
        #     print(f"user_screen_name:{rep_status['user']['screen_name']}")
        #     print(f"user_name:{rep_status['user']['name']}")

        #     # 抽選する
        #     sump = 0
        #     yourp = random.random() * 100
        #     print(f"抽選値：{yourp}")
        #     lot = None
        #     for p in status["lot_pro"]:
        #         sump += int(p["pro"])
        #         if yourp <= sump:
        #             lot = p["name"]
        #             break

        #     # リプライメッセージ作成
        #     if lot is not None:
        #         message = f'{rep_status["user"]["name"]}さん、引用リツイートありがとうございます！\n「{lot}」が当選しました。\n\n※このツイートはbotからの自動送信です #抽選bot'
        #     else:
        #         message = f'{rep_status["user"]["name"]}さん、引用リツイートありがとうございます！\n残念ながら、今回は落選してしまいました…\n\n※このツイートはbotからの自動送信です #抽選bot'

        #     # リプライする
        #     print(f"★★★{message}を送信★★★")
        #     if not DEBUG_MODE:
        #         in_reply_to_status_id = rep_status['id_str']
        #         replyResponse = requests.post(
        #             f'https://api.twitter.com/1.1/statuses/update.json',
        #             data={"status": message, "in_reply_to_status_id": in_reply_to_status_id,
        #                   "auto_populate_reply_metadata": True},
        #             auth=getOauth()
        #         ).json()
        #         print(replyResponse)
        #         doneList += [in_reply_to_status_id]
        #     print(f"exec")

        print("★retweeted★")
        for rep_status in retweetedList:

            if rep_status['retweeted_status']["id_str"] != tweet_id:
                continue

            if rep_status['id_str'] in doneList or rep_status['user']['screen_name'] == SCREEN_NAME:
                print(f"{rep_status['user']['name']} reply done")
                continue

            print(f"text:{rep_status['full_text']}")
            print(f"tweet_id:{rep_status['id_str']}")
            print(f"user_id:{rep_status['user']['id_str']}")
            print(f"user_screen_name:{rep_status['user']['screen_name']}")
            print(f"user_name:{rep_status['user']['name']}")

            # 抽選する
            sump = 0
            yourp = random.random() * 100
            print(f"抽選値：{yourp}")
            lot = None
            for p in status["lot_pro"]:
                sump += int(p["pro"])
                if yourp <= sump:
                    lot = p["name"]
                    break

            # リプライメッセージ作成
            if lot is not None:
                message = f'{rep_status["user"]["name"]}さん、リツイートありがとうございます！\n「{lot}」が当選しました。\n\n※このツイートはbotからの自動送信です #抽選bot'
                #message = f'@{rep_status["user"]["screen_name"]} {rep_status["user"]["name"]}さん、リツイートありがとうございます！\n「{lot}」が当選しました。\n\n※このツイートはbotからの自動送信です #抽選bot'
            else:
                message = f'{rep_status["user"]["name"]}さん、リツイートありがとうございます！\n残念ながら、今回は落選してしまいました…\n\n※このツイートはbotからの自動送信です #抽選bot'
                #message = f'@{rep_status["user"]["screen_name"]} {rep_status["user"]["name"]}さん、リツイートありがとうございます！\n残念ながら、今回は落選してしまいました…\n\n※このツイートはbotからの自動送信です #抽選bot'

            # リプライする
            print(f"★★★{message}を送信★★★")
            if not DEBUG_MODE:
                in_reply_to_status_id = rep_status['id_str']
                replyResponse = requests.post(
                    f'https://api.twitter.com/1.1/statuses/update.json',
                    data={"status": message, "in_reply_to_status_id": in_reply_to_status_id,
                          "auto_populate_reply_metadata": True},
                    auth=getOauth()
                ).json()
                print(replyResponse)
                doneList += [in_reply_to_status_id]
            print(f"exec")

    print(doneList)
    if not DEBUG_MODE:
        putParam("doneList", doneList)
        putParam("tweetList", tweetList)

def lambda_handler(event, context):

    try:
        main()

    except:
        import traceback
        traceback.print_exc()
