import os
import time
import base64
import hashlib
import random
import string
import struct
import socket
from typing import Optional
from xml.etree import ElementTree as ET

import requests
from fastapi import FastAPI, Request, Response, HTTPException
from Crypto.Cipher import AES


app = FastAPI(title="WeCom Copenhagen Bot")

# =========================
# 环境变量
# =========================
WECOM_TOKEN = os.getenv("WECOM_TOKEN", "")
WECOM_AES_KEY = os.getenv("WECOM_AES_KEY", "")
WECOM_CORP_ID = os.getenv("WECOM_CORP_ID", "")

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
HOLIDAY_API_URL = "https://date.nager.at/api/v3/publicholidays/{year}/DK"

COPENHAGEN_LAT = 55.6761
COPENHAGEN_LON = 12.5683
COPENHAGEN_TZ = "Europe/Copenhagen"


# =========================
# 企业微信加解密
# =========================

BLOCK_SIZE = 32


def sha1_signature(token: str, timestamp: str, nonce: str, encrypt: str) -> str:
    parts = [token, timestamp, nonce, encrypt]
    parts.sort()
    raw = "".join(parts).encode("utf-8")
    return hashlib.sha1(raw).hexdigest()


def pkcs7_pad(data: bytes) -> bytes:
    pad_len = BLOCK_SIZE - (len(data) % BLOCK_SIZE)
    if pad_len == 0:
        pad_len = BLOCK_SIZE
    return data + bytes([pad_len]) * pad_len


def pkcs7_unpad(data: bytes) -> bytes:
    pad_len = data[-1]
    if pad_len < 1 or pad_len > BLOCK_SIZE:
        raise ValueError("invalid pkcs7 padding")
    return data[:-pad_len]


def get_random_str(length: int = 16) -> str:
    return "".join(random.sample(string.ascii_letters + string.digits, length))


class WXBizMsgCrypt:
    def __init__(self, token: str, encoding_aes_key: str, receive_id: str):
        self.token = token
        self.receive_id = receive_id
        self.key = base64.b64decode(encoding_aes_key + "=")
        if len(self.key) != 32:
            raise ValueError("invalid EncodingAESKey")

    def verify_url(self, msg_signature: str, timestamp: str, nonce: str, echostr: str) -> str:
        signature = sha1_signature(self.token, timestamp, nonce, echostr)
        if signature != msg_signature:
            raise ValueError("signature not match")
        return self._decrypt(echostr)

    def decrypt_msg(self, msg_signature: str, timestamp: str, nonce: str, post_data: str) -> str:
        xml_tree = ET.fromstring(post_data)
        encrypt = xml_tree.findtext("Encrypt")
        if not encrypt:
            raise ValueError("Encrypt not found")

        signature = sha1_signature(self.token, timestamp, nonce, encrypt)
        if signature != msg_signature:
            raise ValueError("signature not match")

        return self._decrypt(encrypt)

    def encrypt_msg(self, reply_xml: str, nonce: str, timestamp: Optional[str] = None) -> str:
        if timestamp is None:
            timestamp = str(int(time.time()))
        encrypt = self._encrypt(reply_xml)
        signature = sha1_signature(self.token, timestamp, nonce, encrypt)

        return f"""<xml>
<Encrypt><![CDATA[{encrypt}]]></Encrypt>
<MsgSignature><![CDATA[{signature}]]></MsgSignature>
<TimeStamp>{timestamp}</TimeStamp>
<Nonce><![CDATA[{nonce}]]></Nonce>
</xml>"""

    def _encrypt(self, raw_xml: str) -> str:
        raw = raw_xml.encode("utf-8")
        msg_len = struct.pack("!I", len(raw))
        plaintext = get_random_str(16).encode("utf-8") + msg_len + raw + self.receive_id.encode("utf-8")
        padded = pkcs7_pad(plaintext)

        cipher = AES.new(self.key, AES.MODE_CBC, self.key[:16])
        encrypted = cipher.encrypt(padded)
        return base64.b64encode(encrypted).decode("utf-8")

    def _decrypt(self, encrypt_text: str) -> str:
        cipher = AES.new(self.key, AES.MODE_CBC, self.key[:16])
        encrypted = base64.b64decode(encrypt_text)
        decrypted = cipher.decrypt(encrypted)
        decrypted = pkcs7_unpad(decrypted)

        content = decrypted[16:]
        xml_len = struct.unpack("!I", content[:4])[0]
        xml_content = content[4:4 + xml_len]
        from_receive_id = content[4 + xml_len:].decode("utf-8")

        if from_receive_id != self.receive_id:
            raise ValueError("receive_id not match")

        return xml_content.decode("utf-8")


crypt = None


@app.on_event("startup")
def startup_event():
    global crypt
    if not (WECOM_TOKEN and WECOM_AES_KEY and WECOM_CORP_ID):
        raise RuntimeError("Missing required env vars: WECOM_TOKEN / WECOM_AES_KEY / WECOM_CORP_ID")
    crypt = WXBizMsgCrypt(WECOM_TOKEN, WECOM_AES_KEY, WECOM_CORP_ID)


# =========================
# 哥本哈根信息查询
# =========================

def weather_code_to_text(code: Optional[int]) -> str:
    mapping = {
        0: "晴",
        1: "大致晴朗",
        2: "局部多云",
        3: "阴",
        45: "雾",
        48: "冻雾",
        51: "小毛毛雨",
        53: "毛毛雨",
        55: "强毛毛雨",
        61: "小雨",
        63: "中雨",
        65: "大雨",
        71: "小雪",
        73: "中雪",
        75: "大雪",
        80: "阵雨",
        81: "较强阵雨",
        82: "强阵雨",
        95: "雷暴",
    }
    if code is None:
        return "未知"
    return mapping.get(code, f"未知天气代码({code})")


def get_copenhagen_status() -> str:
    params = {
        "latitude": COPENHAGEN_LAT,
        "longitude": COPENHAGEN_LON,
        "current": "temperature_2m,weather_code,wind_speed_10m",
        "timezone": COPENHAGEN_TZ,
    }
    r = requests.get(OPEN_METEO_URL, params=params, timeout=15)
    r.raise_for_status()
    weather_data = r.json()

    current = weather_data.get("current", {})
    now_str = current.get("time", "")
    temp = current.get("temperature_2m")
    code = current.get("weather_code")
    wind = current.get("wind_speed_10m")

    if not now_str:
        raise ValueError("weather API missing current.time")

    date_str = now_str[:10]
    time_str = now_str[11:16]

    holiday_resp = requests.get(HOLIDAY_API_URL.format(year=date_str[:4]), timeout=15)
    holiday_resp.raise_for_status()
    holidays = holiday_resp.json()

    today_holidays = [h for h in holidays if h.get("date") == date_str]
    if today_holidays:
        holiday_text = "是，" + " / ".join(
            h.get("localName") or h.get("name") or "未知假期" for h in today_holidays
        )
    else:
        holiday_text = "不是"

    msg = (
        f"哥本哈根最新信息：\n"
        f"时间：{date_str} {time_str}\n"
        f"天气：{weather_code_to_text(code)}\n"
        f"温度：{temp}°C\n"
        f"风速：{wind} km/h\n"
        f"今天是否为丹麦公共假期：{holiday_text}"
    )
    return msg


def build_help_text() -> str:
    return (
        "可用指令：\n"
        "1. 哥本哈根\n"
        "2. 丹麦天气\n"
        "3. 时间\n"
        "4. 假期\n\n"
        "发送以上任意关键词，我会返回哥本哈根当前时间、天气和丹麦公共假期信息。"
    )


def handle_text_query(content: str) -> str:
    q = (content or "").strip().lower()

    trigger_words = ["哥本哈根", "丹麦", "天气", "时间", "假期", "copenhagen", "denmark", "holiday", "weather", "time"]

    if q in {"help", "?", "菜单", "帮助"}:
        return build_help_text()

    if any(word in q for word in trigger_words):
        try:
            return get_copenhagen_status()
        except Exception as e:
            return f"查询失败：{e}"

    return "我目前支持：哥本哈根 / 丹麦天气 / 时间 / 假期。发送“帮助”查看说明。"


# =========================
# XML 处理
# =========================

def parse_incoming_xml(xml_text: str) -> dict:
    root = ET.fromstring(xml_text)
    return {
        "ToUserName": root.findtext("ToUserName", default=""),
        "FromUserName": root.findtext("FromUserName", default=""),
        "MsgType": root.findtext("MsgType", default=""),
        "Content": root.findtext("Content", default=""),
        "MsgId": root.findtext("MsgId", default=""),
        "CreateTime": root.findtext("CreateTime", default=""),
    }


def build_text_reply(to_user: str, from_user: str, content: str) -> str:
    now_ts = int(time.time())
    return f"""<xml>
<ToUserName><![CDATA[{to_user}]]></ToUserName>
<FromUserName><![CDATA[{from_user}]]></FromUserName>
<CreateTime>{now_ts}</CreateTime>
<MsgType><![CDATA[text]]></MsgType>
<Content><![CDATA[{content}]]></Content>
</xml>"""


# =========================
# HTTP 接口
# =========================

@app.get("/")
def health():
    return {"ok": True, "service": "wecom-copenhagen-bot"}


@app.get("/wecom/callback")
def verify_wecom_url(msg_signature: str, timestamp: str, nonce: str, echostr: str):
    try:
        plain = crypt.verify_url(msg_signature, timestamp, nonce, echostr)
        return Response(content=plain, media_type="text/plain")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"verify failed: {e}")


@app.post("/wecom/callback")
async def receive_wecom_message(request: Request):
    msg_signature = request.query_params.get("msg_signature", "")
    timestamp = request.query_params.get("timestamp", "")
    nonce = request.query_params.get("nonce", "")

    raw_body = (await request.body()).decode("utf-8")

    try:
        plain_xml = crypt.decrypt_msg(msg_signature, timestamp, nonce, raw_body)
        incoming = parse_incoming_xml(plain_xml)

        msg_type = incoming.get("MsgType", "")
        from_user = incoming.get("FromUserName", "")
        to_user = incoming.get("ToUserName", "")

        if msg_type == "text":
            reply_text = handle_text_query(incoming.get("Content", ""))
        else:
            reply_text = "目前只支持文本消息。发送“帮助”查看可用命令。"

        reply_xml = build_text_reply(
            to_user=from_user,
            from_user=to_user,
            content=reply_text,
        )
        encrypted_reply = crypt.encrypt_msg(reply_xml, nonce=nonce, timestamp=timestamp)
        return Response(content=encrypted_reply, media_type="application/xml")

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"message handling failed: {e}")