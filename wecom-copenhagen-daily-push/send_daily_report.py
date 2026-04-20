import os
import requests
from datetime import datetime

# =========================
# 环境变量
# =========================
WECOM_CORP_ID = os.getenv("WECOM_CORP_ID", "")
WECOM_CORP_SECRET = os.getenv("WECOM_CORP_SECRET", "")
WECOM_AGENT_ID = os.getenv("WECOM_AGENT_ID", "")
WECOM_TOUSER = os.getenv("WECOM_TOUSER", "")
WECOM_WEBHOOK_URL = os.getenv("WECOM_WEBHOOK_URL", "")
WECOM_WEBHOOK_KEY = os.getenv("WECOM_WEBHOOK_KEY", "")

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
HOLIDAY_API_URL = "https://date.nager.at/api/v3/publicholidays/{year}/DK"

COPENHAGEN_LAT = 55.6761
COPENHAGEN_LON = 12.5683
COPENHAGEN_TZ = "Europe/Copenhagen"


def weather_code_to_text(code: int) -> str:
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
    return mapping.get(code, f"未知天气代码({code})")


def get_access_token() -> str:
    if not WECOM_CORP_ID or not WECOM_CORP_SECRET:
        raise ValueError("缺少 WECOM_CORP_ID 或 WECOM_CORP_SECRET")

    url = "https://qyapi.weixin.qq.com/cgi-bin/gettoken"
    params = {
        "corpid": WECOM_CORP_ID,
        "corpsecret": WECOM_CORP_SECRET
    }
    resp = requests.get(url, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    if data.get("errcode") != 0:
        raise ValueError(f"获取 access_token 失败: {data}")

    return data["access_token"]


def get_copenhagen_status() -> str:
    params = {
        "latitude": COPENHAGEN_LAT,
        "longitude": COPENHAGEN_LON,
        "current": "temperature_2m,weather_code,wind_speed_10m",
        "timezone": COPENHAGEN_TZ,
    }
    resp = requests.get(OPEN_METEO_URL, params=params, timeout=15)
    resp.raise_for_status()
    weather_data = resp.json()

    current = weather_data.get("current", {})
    now_str = current.get("time", "")
    temp = current.get("temperature_2m")
    weather_code = current.get("weather_code")
    wind_speed = current.get("wind_speed_10m")

    if not now_str:
        raise ValueError("天气接口未返回当前时间")

    dt = datetime.fromisoformat(now_str)
    date_str = dt.strftime("%Y-%m-%d")
    time_str = dt.strftime("%H:%M")

    holiday_resp = requests.get(HOLIDAY_API_URL.format(year=date_str[:4]), timeout=15)
    holiday_resp.raise_for_status()
    holidays = holiday_resp.json()

    today_holidays = [h for h in holidays if h.get("date") == date_str]
    if today_holidays:
        holiday_text = "是，" + " / ".join(
            h.get("localName") or h.get("name") or "未知假期"
            for h in today_holidays
        )
    else:
        holiday_text = "不是"

    msg = (
        f"哥本哈根每日播报\n"
        f"时间：{date_str} {time_str}\n"
        f"天气：{weather_code_to_text(weather_code)}\n"
        f"温度：{temp}°C\n"
        f"风速：{wind_speed} km/h\n"
        f"今天是否为丹麦公共假期：{holiday_text}"
    )
    return msg


def send_wecom_text(content: str) -> dict:
    webhook_url = build_wecom_webhook_url()
    if webhook_url:
        return send_wecom_webhook_text(content, webhook_url)

    if not WECOM_AGENT_ID or not WECOM_TOUSER:
        raise ValueError("缺少 WECOM_AGENT_ID 或 WECOM_TOUSER")

    access_token = get_access_token()
    url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={access_token}"

    payload = {
        "touser": WECOM_TOUSER,
        "msgtype": "text",
        "agentid": int(WECOM_AGENT_ID),
        "text": {
            "content": content
        },
        "safe": 0
    }

    resp = requests.post(url, json=payload, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    if data.get("errcode") != 0:
        raise ValueError(f"发送企业微信消息失败: {data}")

    return data


def build_wecom_webhook_url() -> str:
    if WECOM_WEBHOOK_URL:
        return WECOM_WEBHOOK_URL
    if WECOM_WEBHOOK_KEY:
        return f"https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key={WECOM_WEBHOOK_KEY}"
    return ""


def send_wecom_webhook_text(content: str, webhook_url: str) -> dict:
    payload = {
        "msgtype": "text",
        "text": {
            "content": content
        }
    }

    resp = requests.post(webhook_url, json=payload, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    if data.get("errcode") != 0:
        raise ValueError(f"发送企业微信机器人消息失败: {data}")

    return data


def main():
    content = get_copenhagen_status()
    result = send_wecom_text(content)
    print("发送成功:", result)


if __name__ == "__main__":
    main()
