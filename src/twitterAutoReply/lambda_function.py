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
    item = table.get_item(Key={"key": key})
    if "Item" in item:
        return item["Item"]
    else:
        return None


def putItem(data):
    dynamoDB = boto3.resource("dynamodb")
    table = dynamoDB.Table("twitterLotterBot")
    table.put_item(Item=data)


def main():

    ngList = getParam("ngList")

    # 自分宛のリプライ最新から10件を全て取得
    response = requests.get(
        f'https://api.twitter.com/1.1/statuses/mentions_timeline.json?count=20',
        auth=getOauth()
    ).json()

    # その中から、指定した元ツイートに対してのリプライのみに絞り込む
    in_reply_to_status_id = 1231358267516809216  # 1231087256556859392
    response = list(
        filter(lambda x: x["in_reply_to_status_id"] == in_reply_to_status_id, response))

    # 未リプライの物のみに絞り込む
    doneList = requests.get(
        f'https://api.twitter.com/1.1/statuses/user_timeline.json?screen_name={SCREEN_NAME}&count=100',
        auth=getOauth()
    ).json()
    doneList = list(map(lambda x: x["in_reply_to_status_id"], doneList))
    print(doneList)

    response = list(filter(lambda x: x["id"] not in doneList, response))
    print(response)

    # 扱いやすいように成型
    replyList = list(map(lambda x: {"id": x["user"]["id"], "name": x["user"]["name"],
                                    "profile": x["user"]["description"], "replyId": x["id"], "ng": False}, response))
    print(replyList)

    # 名前の切り抜き
    for idx, r in enumerate(replyList):
        name = replyList[idx]["name"]
        name = name.split("@")[0]
        name = name.split("｜")[0]

        # 空になってしまったら、元々の名前を復活
        if len(name) == 0:
            name = replyList[idx]["name"]

        # 切り抜いた結果of切り抜けなかった結果15文字以内なら文字数で切り取り
        if len(name) <= 15:
            replyList[idx]["name"] = name
        else:
            replyList[idx]["name"] = f"{name[0:15]}…"

    # 最新のツイートを10件取得する
    option = 'count=10&exclude_replies=true&include_rts=false'
    for idx, r in enumerate(replyList):
        user_timeline = requests.get(
            f'https://api.twitter.com/1.1/statuses/user_timeline.json?id={r["id"]}&{option}',
            auth=getOauth()
        ).json()
        replyList[idx]["tweetList"] = list(
            map(lambda x: x["text"], user_timeline))
        replyList[idx]["tweetIdList"] = list(
            map(lambda x: x["id"], user_timeline))
    print(replyList)

    # NGワードチェック
    print("NGワードチェック")
    for idx, reply in enumerate(replyList):
        # プロフィールをチェック
        if len(list(filter(lambda ng: ng in reply["profile"], ngList))):
            print(f"{reply['name']}:ng")
            print(list(filter(lambda ng: ng in reply["profile"], ngList)))
            replyList[idx]["ng"] = True
            replyList[idx]["ngReason"] = "プロフィールにNGワードが含まれている"
        elif len(list(filter(lambda x: len(list(filter(lambda ng: ng in x, ngList))), reply["tweetList"]))):
            print(f"{reply['name']}:ng")
            print(list(filter(lambda x: len(
                list(filter(lambda ng: ng in x, ngList))), reply["tweetList"])))
            replyList[idx]["ng"] = True
            replyList[idx]["ngReason"] = "ツイートにNGワードが含まれている"
        else:
            print(f"{reply['name']}:ok")

    # リンク数チェック
    print("リンク数チェック")
    for idx, reply in enumerate(replyList):
        # ツイートをチェック
        if len(list(filter(lambda x: x.count("http") >= 2, reply["tweetList"]))):
            print(f"{reply['name']}:ng")
            replyList[idx]["ng"] = True
            replyList[idx]["ngReason"] = "ツイートに過剰なリンクがある"
        else:
            print(f"{reply['name']}:ok")

    # 重複リンク数チェック
    print("重複リンク数チェック")
    pattern = "https?://[\w/:%#\$&\?\(\)~\.=\+\-]+"
    for idx, reply in enumerate(replyList):
        # urlを抽出 ※既に1ツイート内に複数urlある場合は除外しているので、ここに来た時には、必ず1ツイート0～1url
        # まずurlを含むものだけに絞る
        urlTweetList = list(
            filter(lambda x: x.count("http") == 1, reply["tweetList"]))
        print(f"urlTweetList:{urlTweetList}")
        # urlを抽出
        urlList = list(map(lambda x: re.findall(pattern, x)[0], urlTweetList))
        print(f"urlList:{urlList}")
        # urlListのそれぞれのurlの出現回数をカウントしてくれる ※要import collections
        counter = collections.Counter(urlList)
        print(f"counter:{counter}")

        if len(list(filter(lambda x: x >= 3, counter.values()))):
            print(f"{reply['name']}:ng")
            replyList[idx]["ng"] = True
            replyList[idx]["ngReason"] = "ツイートに過剰な重複リンクがある"
        else:
            print(f"{reply['name']}:ok")

    warnList = ["RT企画", "固定ツイート", "固ツイ", "リツイート"]
    # RT企画数チェック
    print("RT企画数チェック")
    for idx, reply in enumerate(replyList):
        if len(list(filter(lambda x: len(list(filter(lambda warn: warn in x, warnList))), reply["tweetList"]))) >= 3:
            print(f"{reply['name']}:ng")
            replyList[idx]["ng"] = True
            replyList[idx]["ngReason"] = "過剰なRT企画ツイートがある"
        else:
            print(f"{reply['name']}:ok")

    # 日本語チェック
    print("日本語チェック")
    pattern = "[\u3041-\u309F]+"  # ひらがな
    for idx, reply in enumerate(replyList):
        print(re.findall(pattern, reply["profile"]))
        if len(re.findall(pattern, reply["profile"])) == 0:
            print(f"{reply['name']}:ng")
            replyList[idx]["ng"] = True
            replyList[idx]["ngReason"] = "プロフィールから日本語が検出できない"
        else:
            print(f"{reply['name']}:ok")

    # リプライする
    for reply in replyList:
        if reply["ng"]:
            status = f'{reply["name"]}さん、企画に参加ありがとうございます！\n大変申し訳ありませんが、{reply["ngReason"]}のため、{reply["name"]}さんのツイートはRTできません。\n\n※このツイートはbotからの自動送信です'
        else:
            status = f'{reply["name"]}さん、企画に参加ありがとうございます！\nリプの御礼に{reply["name"]}さんのツイートを最新から3件ほど、RTさせて頂きます♡\n何回でも参加可能なので、またのご参加お待ちしております！\n\n※このツイートはbotからの自動送信です'
        # status = f'{reply["name"]}さん、リプありがとうございます！\n本企画ではリプの御礼に{reply["name"]}さんのツイートを最新から3件ほど、リツイートさせて頂きます♡\nフォロワーが5000人を超えるのをお待ちくださいませ！\n\n※このツイートはbotからの自動送信です'
        in_reply_to_status_id = reply["replyId"]
        print(f"in_reply_to_status_id:{in_reply_to_status_id} exec")
        replyResponse = requests.post(
            f'https://api.twitter.com/1.1/statuses/update.json',
            data={"status": status, "in_reply_to_status_id": in_reply_to_status_id,
                  "auto_populate_reply_metadata": True},
            auth=getOauth()
        ).json()
        print(replyResponse)

        # リツイートする
        if not reply["ng"]:
            for idx in range(3):
                if idx >= len(reply["tweetIdList"]):
                    break
                sleepTime = random.random() * 20
                print(sleepTime)
                time.sleep(sleepTime)

                print(f'{reply["tweetIdList"][idx]}をリツイート')
                response = requests.post(
                    f'https://api.twitter.com/1.1/statuses/retweet/{reply["tweetIdList"][idx]}.json',
                    auth=getOauth()
                ).json()
                print(response)


def lambda_handler(event, context):

    try:
        main()

    except:
        import traceback
        traceback.print_exc()
