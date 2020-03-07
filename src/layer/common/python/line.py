import json
import boto3
import re
import os
import datetime
import urllib.request
import traceback


USER_ID = os.environ['USERID']
ACCESS_TOKEN = {}

def getAccessToken(shopId="dev", manage=False):
    global ACCESS_TOKEN
    if not shopId in ACCESS_TOKEN:
        dynamoDB = boto3.resource("dynamodb")
        table = dynamoDB.Table("userMaster")  # DynamoDBのテーブル名
        item = table.get_item(Key={"userId": shopId, "key": "ユーザー設定"})

        ACCESS_TOKEN[shopId] = item["Item"]["data"]

    if manage:
        return ACCESS_TOKEN[shopId]["AccessTokenManage"]
    else:
        return ACCESS_TOKEN[shopId]["AccessToken"]


def manageMessage(mes, shopId="dev", to=None):
    message(mes, to, True, shopId)


def message(mes, to=None, isManage=False, shopId="dev"):
    url = "https://api.line.me/v2/bot/message/push"

    messages = []

    if type(mes) is str:
        messages += [{
            'type': 'text',
            'text': mes
        }]
    else:
        messages += [{"type": "template",
                      "altText": mes["text"],
                      "template": mes}]

    print(messages)

    if to is None:
        to = USER_ID

    postData = {
        "to": to,
        "messages": messages
    }
    accessToken = getAccessToken(shopId, isManage)

    print(f"accessToken:{accessToken}")

    headers = {
        "Content-Type": "application/json",
        'Authorization': 'Bearer ' + accessToken,
    }

    req = urllib.request.Request(url, json.dumps(postData).encode(), headers)

    with urllib.request.urlopen(req) as res:
        body = json.loads(res.read())
