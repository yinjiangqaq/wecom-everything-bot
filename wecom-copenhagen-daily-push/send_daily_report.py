import html
import os
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urlencode
from xml.etree import ElementTree
from zoneinfo import ZoneInfo

import requests

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
GOOGLE_NEWS_RSS_URL = "https://news.google.com/rss/search"
GOOGLE_TRANSLATE_URL = "https://translate.googleapis.com/translate_a/single"

COPENHAGEN_LAT = 55.6761
COPENHAGEN_LON = 12.5683
COPENHAGEN_TZ = "Europe/Copenhagen"
HTTP_TIMEOUT = 15
NEWS_ITEMS_PER_CATEGORY = int(os.getenv("NEWS_ITEMS_PER_CATEGORY", "1"))

REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36"
    )
}

NEWS_CATEGORY_QUERIES = [
    ("交通", "Copenhagen traffic OR Copenhagen metro OR Copenhagen train OR Copenhagen road"),
    ("天气", "Copenhagen weather OR Copenhagen storm OR Copenhagen rain OR Copenhagen climate"),
    ("节日", "Copenhagen holiday OR Copenhagen festival OR Copenhagen celebration OR Copenhagen event"),
    ("文化活动", "Copenhagen culture OR Copenhagen museum OR Copenhagen exhibition OR Copenhagen concert"),
    ("本地", "Copenhagen local news OR Copenhagen city council OR Copenhagen neighborhood"),
]

_translation_cache = {}
LOCAL_NEWS_TZ = ZoneInfo(COPENHAGEN_TZ)


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
    params = {"corpid": WECOM_CORP_ID, "corpsecret": WECOM_CORP_SECRET}
    resp = requests.get(url, params=params, headers=REQUEST_HEADERS, timeout=HTTP_TIMEOUT)
    resp.raise_for_status()
    data = resp.json()

    if data.get("errcode") != 0:
        raise ValueError(f"获取 access_token 失败: {data}")

    return data["access_token"]


def get_copenhagen_now() -> tuple[datetime, dict]:
    params = {
        "latitude": COPENHAGEN_LAT,
        "longitude": COPENHAGEN_LON,
        "current": "temperature_2m,weather_code,wind_speed_10m",
        "timezone": COPENHAGEN_TZ,
    }
    resp = requests.get(
        OPEN_METEO_URL,
        params=params,
        headers=REQUEST_HEADERS,
        timeout=HTTP_TIMEOUT,
    )
    resp.raise_for_status()
    weather_data = resp.json()

    current = weather_data.get("current", {})
    now_str = current.get("time", "")
    if not now_str:
        raise ValueError("天气接口未返回当前时间")

    dt = datetime.fromisoformat(now_str)
    return dt, current


def get_holiday_text(date_str: str) -> str:
    holiday_resp = requests.get(
        HOLIDAY_API_URL.format(year=date_str[:4]),
        headers=REQUEST_HEADERS,
        timeout=HTTP_TIMEOUT,
    )
    holiday_resp.raise_for_status()
    holidays = holiday_resp.json()

    today_holidays = [h for h in holidays if h.get("date") == date_str]
    if today_holidays:
        return "是，" + " / ".join(
            h.get("localName") or h.get("name") or "未知假期"
            for h in today_holidays
        )
    return "不是"


def build_news_rss_url(query: str) -> str:
    params = {
        "q": f"{query} when:1d",
        "hl": "en-US",
        "gl": "US",
        "ceid": "US:en",
    }
    return f"{GOOGLE_NEWS_RSS_URL}?{urlencode(params)}"


def strip_title_source(title: str, source: str) -> str:
    if not source:
        return title
    suffix = f" - {source}"
    if title.endswith(suffix):
        return title[: -len(suffix)].strip()
    return title.strip()


def normalize_title(title: str) -> str:
    return re.sub(r"\s+", " ", title).strip().lower()


def format_news_time(pub_dt: datetime | None) -> str:
    if not pub_dt:
        return ""
    local_dt = pub_dt.astimezone(LOCAL_NEWS_TZ)
    return local_dt.strftime("%m-%d %H:%M")


def translate_text_to_zh(text: str) -> str:
    normalized = text.strip()
    if not normalized:
        return normalized
    if normalized in _translation_cache:
        return _translation_cache[normalized]

    params = {
        "client": "gtx",
        "sl": "auto",
        "tl": "zh-CN",
        "dt": "t",
        "q": normalized,
    }
    try:
        resp = requests.get(
            GOOGLE_TRANSLATE_URL,
            params=params,
            headers=REQUEST_HEADERS,
            timeout=HTTP_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        translated = "".join(part[0] for part in data[0] if part and part[0]).strip()
        if translated:
            _translation_cache[normalized] = translated
            return translated
    except requests.RequestException:
        pass
    except (ValueError, IndexError, TypeError):
        pass

    _translation_cache[normalized] = normalized
    return normalized


def fetch_news_items(query: str, seen_titles: set[str]) -> list[dict]:
    resp = requests.get(
        build_news_rss_url(query),
        headers=REQUEST_HEADERS,
        timeout=HTTP_TIMEOUT,
    )
    resp.raise_for_status()

    root = ElementTree.fromstring(resp.content)
    items = []

    for item in root.findall("./channel/item"):
        raw_title = html.unescape(item.findtext("title", default="").strip())
        source = html.unescape(item.findtext("source", default="").strip())
        clean_title = strip_title_source(raw_title, source)
        title_key = normalize_title(clean_title)
        if not clean_title or not title_key or title_key in seen_titles:
            continue

        pub_date = item.findtext("pubDate", default="").strip()
        pub_dt = None
        if pub_date:
            try:
                parsed = parsedate_to_datetime(pub_date)
                pub_dt = parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
            except (TypeError, ValueError):
                pub_dt = None

        items.append(
            {
                "title": clean_title,
                "source": source or "Google News",
                "published_at": pub_dt,
            }
        )
        seen_titles.add(title_key)

        if len(items) >= NEWS_ITEMS_PER_CATEGORY:
            break

    return items


def format_news_section() -> str:
    lines = ["当日新闻："]
    seen_titles = set()

    for category_name, query in NEWS_CATEGORY_QUERIES:
        try:
            items = fetch_news_items(query, seen_titles)
        except requests.RequestException:
            items = []
        except ElementTree.ParseError:
            items = []

        lines.append(f"【{category_name}】")
        if not items:
            lines.append("- 暂无检索到相关更新")
            continue

        for item in items:
            translated_title = translate_text_to_zh(item["title"])
            time_text = format_news_time(item["published_at"])
            meta = item["source"]
            if time_text:
                meta = f"{meta}，{time_text}"
            lines.append(f"- {translated_title}（{meta}）")

    return "\n".join(lines)


def get_copenhagen_status() -> str:
    dt, current = get_copenhagen_now()
    date_str = dt.strftime("%Y-%m-%d")
    time_str = dt.strftime("%H:%M")
    temp = current.get("temperature_2m")
    weather_code = current.get("weather_code")
    wind_speed = current.get("wind_speed_10m")
    holiday_text = get_holiday_text(date_str)
    news_section = format_news_section()

    msg = (
        f"哥本哈根每日播报\n"
        f"时间：{date_str} {time_str}\n"
        f"天气：{weather_code_to_text(weather_code)}\n"
        f"温度：{temp}°C\n"
        f"风速：{wind_speed} km/h\n"
        f"今天是否为丹麦公共假期：{holiday_text}\n"
        f"\n"
        f"{news_section}"
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
        "text": {"content": content},
        "safe": 0,
    }

    resp = requests.post(url, json=payload, headers=REQUEST_HEADERS, timeout=HTTP_TIMEOUT)
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
    payload = {"msgtype": "text", "text": {"content": content}}

    resp = requests.post(webhook_url, json=payload, headers=REQUEST_HEADERS, timeout=HTTP_TIMEOUT)
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
