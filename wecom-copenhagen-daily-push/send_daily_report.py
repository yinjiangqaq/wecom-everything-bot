import html
import json
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
CPHPOST_RSS_URL = "https://cphpost.dk/rss-feed/"
CPH_POLICE_RSS_URL = "https://via.ritzau.dk/rss/short-messages/latest?publisherId=90685"
TOO_GOOD_TO_GO_URL = "https://www.toogoodtogo.com/"
ETILBUDSAVIS_URL = "https://etilbudsavis.dk/"
MINETILBUD_URL = "https://minetilbud.dk/"
MATAS_HAND_SANITIZER_URL = "https://www.matas.dk/medicin-pleje/hygiejne/haandsprit"
UNGDOMSKORT_URL = "https://ungdomskort.dk/english"
DSB_ORANGE_URL = "https://www.dsb.dk/en/find-produkter-og-services/orange/"
DSB_ORANGE_FRI_URL = "https://www.dsb.dk/en/tickets-and-services/orange-fri/"
REJSEKORT_IMPORTANT_DATES_URL = "https://www.rejsekort.dk/en/luk/Vigtige-datoer/Vigtige-datoer"
REJSEPLANEN_APP_URL = "https://help.rejseplanen.dk/hc/en-us/articles/115002672449-Rejseplanen-s-app"

COPENHAGEN_LAT = 55.6761
COPENHAGEN_LON = 12.5683
COPENHAGEN_TZ = "Europe/Copenhagen"
HTTP_TIMEOUT = 15
NEWS_ITEMS_PER_CATEGORY = int(os.getenv("NEWS_ITEMS_PER_CATEGORY", "1"))
LIFE_INFO_ENABLED = os.getenv("LIFE_INFO_ENABLED", "1").lower() not in {
    "0",
    "false",
    "no",
    "off",
}
LIFE_REFERENCE_ITEM_LIMIT = int(os.getenv("LIFE_REFERENCE_ITEM_LIMIT", "2"))
WECOM_TEXT_MAX_CHARS = int(os.getenv("WECOM_TEXT_MAX_CHARS", "1800"))

KU_PHARMACY_CAMPUS = {
    "name": "KU 药学院 / Department of Pharmacy",
    "address": "Universitetsparken 2, 2100 København Ø",
    "reception_address": "Jagtvej 160, Building 22, 2100 Copenhagen Ø",
    "nearby_bus_lines": ["8A", "42", "184", "185", "15E", "150S"],
}

LIFE_STAPLE_SEARCHES = [
    ("håndsprit", "消毒/免洗洗手液"),
    ("vaskemiddel", "洗衣液"),
    ("toiletpapir", "厕纸/纸巾"),
    ("opvaskemiddel", "洗洁精"),
    ("rugbrød", "黑麦面包"),
    ("brød", "面包"),
]

REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36"
    )
}

COPENHAGEN_KEYWORDS = [
    "copenhagen",
    "kobenhavn",
    "københavn",
    "greater copenhagen",
    "city of copenhagen",
    "cop15",
]

DENMARK_KEYWORDS = [
    "denmark",
    "danish",
    "aarhus",
    "odense",
    "aalborg",
    "roskilde",
    "helsingor",
    "elsinore",
    "jutland",
    "zealand",
    "fyn",
]

GLOBAL_EXCLUDED_KEYWORDS = [
    "japan",
    "tokyo",
    "china",
    "beijing",
    "russia",
    "ukraine",
    "gaza",
    "israel",
    "trump",
    "washington",
    "taiwan",
    "earthquake",
    "tsunami",
    "pope",
    "vatican",
]

NEWS_CATEGORY_CONFIGS = [
    {
        "name": "交通",
        "queries": [
            "site:politi.dk Copenhagen traffic OR Copenhagen metro OR Copenhagen train OR Copenhagen road",
            "site:cphpost.dk Copenhagen traffic OR metro OR rail OR road OR commute",
        ],
        "rss_urls": [CPH_POLICE_RSS_URL],
        "topic_keywords": [
            "traffic",
            "metro",
            "train",
            "rail",
            "road",
            "bus",
            "station",
            "commute",
            "transport",
            "closure",
            "closed",
            "delay",
            "disruption",
            "accident",
            "police",
        ],
        "location_keywords": COPENHAGEN_KEYWORDS + DENMARK_KEYWORDS,
        "exclude_keywords": GLOBAL_EXCLUDED_KEYWORDS,
    },
    {
        "name": "天气",
        "queries": [
            "site:cphpost.dk Copenhagen weather OR storm OR rain OR snow OR wind OR flood",
            "Copenhagen weather storm rain wind snow flood site:thelocal.dk OR site:cphpost.dk",
        ],
        "rss_urls": [],
        "topic_keywords": [
            "weather",
            "storm",
            "rain",
            "snow",
            "wind",
            "flood",
            "icy",
            "ice",
            "temperature",
            "forecast",
            "heat",
            "cold",
            "climate",
        ],
        "location_keywords": COPENHAGEN_KEYWORDS + DENMARK_KEYWORDS,
        "exclude_keywords": GLOBAL_EXCLUDED_KEYWORDS,
    },
    {
        "name": "节日",
        "queries": [
            "site:cphpost.dk Copenhagen holiday OR festival OR parade OR celebration",
            "Copenhagen holiday festival celebration site:visitcopenhagen.com OR site:cphpost.dk",
        ],
        "rss_urls": [],
        "topic_keywords": [
            "holiday",
            "festival",
            "parade",
            "celebration",
            "easter",
            "christmas",
            "public holiday",
            "tradition",
            "festive",
        ],
        "location_keywords": COPENHAGEN_KEYWORDS + DENMARK_KEYWORDS,
        "exclude_keywords": GLOBAL_EXCLUDED_KEYWORDS,
    },
    {
        "name": "文化活动",
        "queries": [
            "site:cphpost.dk Copenhagen museum OR exhibition OR concert OR theatre OR opera OR art OR jazz",
            "Copenhagen culture museum exhibition concert theatre opera art jazz site:visitcopenhagen.com OR site:cphpost.dk",
        ],
        "rss_urls": [],
        "topic_keywords": [
            "culture",
            "museum",
            "exhibition",
            "concert",
            "theatre",
            "theater",
            "opera",
            "art",
            "music",
            "jazz",
            "film",
            "cinema",
            "performance",
        ],
        "location_keywords": COPENHAGEN_KEYWORDS + DENMARK_KEYWORDS,
        "exclude_keywords": GLOBAL_EXCLUDED_KEYWORDS + [
            "government",
            "minister",
            "parliament",
            "negotiation",
            "coalition",
            "election",
            "prime minister",
        ],
    },
    {
        "name": "本地",
        "queries": [
            "site:cphpost.dk Copenhagen city council OR housing OR neighborhood OR school OR hospital",
            "site:international.kk.dk Copenhagen city council OR housing OR neighborhood OR school OR hospital",
            "Copenhagen local news city council housing neighborhood school hospital site:cphpost.dk OR site:international.kk.dk",
        ],
        "rss_urls": [],
        "topic_keywords": [
            "city",
            "council",
            "housing",
            "neighborhood",
            "school",
            "hospital",
            "municipality",
            "district",
            "resident",
            "residents",
            "local",
            "mayor",
            "urban",
            "development",
        ],
        "location_keywords": COPENHAGEN_KEYWORDS + DENMARK_KEYWORDS,
        "exclude_keywords": GLOBAL_EXCLUDED_KEYWORDS,
    },
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


def clean_html_text(text: str) -> str:
    unescaped = html.unescape(text or "")
    no_tags = re.sub(r"<[^>]+>", " ", unescaped)
    return re.sub(r"\s+", " ", no_tags).strip()


def clean_json_string(value: str) -> str:
    try:
        return json.loads(f'"{value}"')
    except json.JSONDecodeError:
        return html.unescape(value)


def build_maps_search_url(query: str) -> str:
    params = {"api": "1", "query": query}
    return f"https://www.google.com/maps/search/?{urlencode(params)}"


def parse_dkk_price(price_text: str) -> float:
    number_match = re.search(r"\d+(?:[.,]\d+)?", price_text)
    if not number_match:
        return 10**9
    return float(number_match.group(0).replace(".", "").replace(",", "."))


def dedupe_preserving_order(values) -> list[str]:
    seen = set()
    result = []
    for value in values:
        normalized = normalize_title(value)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(value.strip())
    return result


def collapse_repeated_product_name(name: str) -> str:
    words = name.split()
    if len(words) < 4 or len(words) % 2:
        return name
    half = len(words) // 2
    if words[:half] == words[half:]:
        return " ".join(words[:half])
    return name


def clean_product_name(name: str) -> str:
    cleaned = re.sub(r"\b\d+\s*(?:stk|ml|l|g|kg|produkter)\b", " ", name, flags=re.I)
    cleaned = re.sub(
        r"\b(?:filtre|mærker|indhold|certificeringer|sortering|mest populære|se alle)\b",
        " ",
        cleaned,
        flags=re.I,
    )
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" -")
    cleaned = collapse_repeated_product_name(cleaned)
    if len(cleaned) > 90:
        cleaned = cleaned[-90:].strip(" -")
    if len(cleaned) < 5:
        return ""
    if any(
        noise in cleaned.lower()
        for noise in [
            "hurtig levering",
            "betalingsmuligheder",
            "find receptmedicin",
            "klub matas",
        ]
    ):
        return ""
    return cleaned


def fetch_matas_hand_sanitizer_examples(limit: int) -> list[dict]:
    try:
        resp = requests.get(
            MATAS_HAND_SANITIZER_URL,
            headers=REQUEST_HEADERS,
            timeout=HTTP_TIMEOUT,
        )
        resp.raise_for_status()
    except requests.RequestException:
        return []

    page_text = clean_html_text(resp.text)
    fragments = re.split(r"Image:\s*", page_text)
    items = []

    for fragment in fragments:
        if "Pris:" not in fragment:
            continue
        price_match = re.search(r"Pris:\s*([0-9]+(?:[.,][0-9]{2})?\s*kr\.?)", fragment)
        if not price_match:
            continue

        name = clean_product_name(fragment[: price_match.start()])
        if not name:
            continue

        items.append(
            {
                "name": name,
                "price": price_match.group(1).replace(" ", ""),
                "source": "Matas",
                "url": MATAS_HAND_SANITIZER_URL,
            }
        )

    unique_items = []
    seen = set()
    for item in sorted(items, key=lambda item: parse_dkk_price(item["price"])):
        key = normalize_title(f"{item['name']} {item['price']}")
        if key in seen:
            continue
        seen.add(key)
        unique_items.append(item)
        if len(unique_items) >= limit:
            break

    return unique_items


def fetch_etilbudsavis_top_searches(limit: int) -> list[str]:
    try:
        resp = requests.get(ETILBUDSAVIS_URL, headers=REQUEST_HEADERS, timeout=HTTP_TIMEOUT)
        resp.raise_for_status()
    except requests.RequestException:
        return []

    raw_titles = re.findall(
        r'"title"\s*:\s*"([^"]+)"\s*,\s*"type"\s*:\s*"search_query"',
        resp.text,
    )
    titles = dedupe_preserving_order(clean_json_string(title) for title in raw_titles)
    return titles[:limit]


def format_campus_life_header() -> list[str]:
    return [
        "留学生活情报（KU 药学院附近）：",
        (
            f"定位：{KU_PHARMACY_CAMPUS['address']}；公交关注 "
            f"{'/'.join(KU_PHARMACY_CAMPUS['nearby_bus_lines'])}"
        ),
    ]


def format_bakery_discount_section() -> list[str]:
    campus_query = f"bakery near {KU_PHARMACY_CAMPUS['address']}"
    return [
        "【面包/临期食品】",
        (
            "- Too Good To Go：把位置设为 Universitetsparken 2，收藏 Østerbro / "
            "Nørrebro 面包店和咖啡店，晚间/关门前更容易刷到 surprise bag。"
        ),
        f"  入口：{TOO_GOOD_TO_GO_URL}",
        f"  地图查附近面包店：{build_maps_search_url(campus_query)}",
    ]


def format_life_goods_section() -> list[str]:
    lines = ["【生活用品/比价】"]

    matas_items = fetch_matas_hand_sanitizer_examples(LIFE_REFERENCE_ITEM_LIMIT)
    if matas_items:
        examples = "；".join(
            f"{item['name']} {item['price']}" for item in matas_items
        )
        lines.append(f"- Matas 消毒用品参考低价：{examples}")
    else:
        lines.append("- 消毒/免洗洗手液：优先查 Matas、Normal、Netto、Lidl 的当周优惠。")

    top_searches = fetch_etilbudsavis_top_searches(12)
    staple_terms = {query for query, _label in LIFE_STAPLE_SEARCHES}
    relevant_searches = [
        title for title in top_searches if normalize_title(title) in staple_terms
    ]
    if relevant_searches:
        lines.append(f"- eTilbudsavis 近期热搜：{' / '.join(relevant_searches[:4])}")

    tracked_labels = "、".join(
        f"{label}({query})" for query, label in LIFE_STAPLE_SEARCHES
    )
    lines.append(f"- 本周建议查：{tracked_labels}")
    lines.append(f"  eTilbudsavis：{ETILBUDSAVIS_URL}")
    lines.append(f"  MineTilbud：{MINETILBUD_URL}")
    lines.append(
        "  附近日用品地图："
        + build_maps_search_url(f"Normal Matas Netto Lidl near {KU_PHARMACY_CAMPUS['address']}")
    )
    return lines


def format_transport_saving_section(now: datetime) -> list[str]:
    lines = ["【交通省钱】"]
    lines.append(
        "- 上学通勤：先用 Rejseplanen 算住址到 Universitetsparken 2 的区数；"
        "每天跨区通勤再比较 Ungdomskort/通勤卡，偶尔出行用 Rejsekort app 或 Rejsebillet。"
    )
    lines.append(f"  Ungdomskort：{UNGDOMSKORT_URL}")
    lines.append(f"  Rejseplanen：{REJSEPLANEN_APP_URL}")
    lines.append(
        "- 城际旅行：提前查 DSB Orange；行程可能变动时优先看 Orange Fri，"
        "通常比临时买标准票更省。"
    )
    lines.append(f"  DSB Orange：{DSB_ORANGE_URL}")
    lines.append(f"  Orange Fri：{DSB_ORANGE_FRI_URL}")

    rejsekort_close_date = datetime(2026, 5, 29, tzinfo=now.tzinfo).date()
    if now.date() <= rejsekort_close_date:
        lines.append(
            "- Rejsekort 提醒：实体卡系统 2026-05-29 关闭，别在旧卡里留太多余额，"
            "优先迁到 Rejsekort app。"
        )
    else:
        lines.append("- Rejsekort 提醒：旧实体卡系统已关闭，优先使用 Rejsekort app / Rejsebillet。")
    lines.append(f"  重要日期：{REJSEKORT_IMPORTANT_DATES_URL}")
    return lines


def format_student_life_section_text(now: datetime) -> str:
    if not LIFE_INFO_ENABLED:
        return ""

    lines = []
    lines.extend(format_campus_life_header())
    lines.extend(format_bakery_discount_section())
    lines.extend(format_life_goods_section())
    lines.extend(format_transport_saving_section(now))
    return "\n".join(lines)


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


def build_item_text(item: dict) -> str:
    return " ".join(
        part
        for part in [
            item.get("title", ""),
            item.get("source", ""),
            item.get("summary", ""),
            item.get("url", ""),
        ]
        if part
    ).lower()


def item_is_copenhagen_specific(item: dict) -> bool:
    haystack = build_item_text(item)
    return contains_any_keyword(haystack, COPENHAGEN_KEYWORDS)


def item_is_denmark_specific(item: dict) -> bool:
    haystack = build_item_text(item)
    return contains_any_keyword(haystack, COPENHAGEN_KEYWORDS + DENMARK_KEYWORDS)


def location_priority(item: dict) -> int:
    if item_is_copenhagen_specific(item):
        return 0
    if item_is_denmark_specific(item):
        return 1
    return 2


def contains_any_keyword(text: str, keywords: list[str]) -> bool:
    return any(keyword.lower() in text for keyword in keywords)


def item_matches_category(
    item: dict,
    topic_keywords: list[str],
    location_keywords: list[str],
    exclude_keywords: list[str],
) -> bool:
    haystack = build_item_text(item)
    if exclude_keywords and contains_any_keyword(haystack, exclude_keywords):
        return False
    if not item_is_denmark_specific(item):
        return False
    if topic_keywords and not contains_any_keyword(haystack, topic_keywords):
        return False
    if location_keywords and not contains_any_keyword(haystack, location_keywords):
        return False
    return True


def news_identity(item: dict) -> str:
    return normalize_title(item.get("title", ""))


def parse_rss_items(root: ElementTree.Element, seen_titles: set[str]) -> list[dict]:
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
                "summary": clean_html_text(item.findtext("description", default="").strip()),
                "url": item.findtext("link", default="").strip(),
                "published_at": pub_dt,
            }
        )
    return items


def fetch_news_items(query: str, seen_titles: set[str]) -> list[dict]:
    resp = requests.get(
        build_news_rss_url(query),
        headers=REQUEST_HEADERS,
        timeout=HTTP_TIMEOUT,
    )
    resp.raise_for_status()
    root = ElementTree.fromstring(resp.content)
    return parse_rss_items(root, seen_titles)


def fetch_rss_feed_items(rss_url: str, seen_titles: set[str]) -> list[dict]:
    resp = requests.get(rss_url, headers=REQUEST_HEADERS, timeout=HTTP_TIMEOUT)
    resp.raise_for_status()
    root = ElementTree.fromstring(resp.content)
    return parse_rss_items(root, seen_titles)


def collect_category_items(category_config: dict, seen_titles: set[str]) -> list[dict]:
    candidates = []
    topic_keywords = category_config.get("topic_keywords", [])
    location_keywords = category_config.get("location_keywords", [])
    exclude_keywords = category_config.get("exclude_keywords", [])

    for rss_url in category_config.get("rss_urls", []):
        try:
            items = fetch_rss_feed_items(rss_url, seen_titles)
        except (requests.RequestException, ElementTree.ParseError):
            continue
        for item in items:
            item_key = news_identity(item)
            if item_key in seen_titles or not item_matches_category(
                item,
                topic_keywords,
                location_keywords,
                exclude_keywords,
            ):
                continue
            candidates.append(item)

    for query in category_config.get("queries", []):
        try:
            items = fetch_news_items(query, seen_titles)
        except (requests.RequestException, ElementTree.ParseError):
            continue
        for item in items:
            item_key = news_identity(item)
            if item_key in seen_titles or not item_matches_category(
                item,
                topic_keywords,
                location_keywords,
                exclude_keywords,
            ):
                continue
            candidates.append(item)

    candidates.sort(key=lambda item: (location_priority(item), item.get("published_at") is None))

    selected = []
    for item in candidates:
        item_key = news_identity(item)
        if item_key in seen_titles:
            continue
        seen_titles.add(item_key)
        selected.append(item)
        if len(selected) >= NEWS_ITEMS_PER_CATEGORY:
            break

    return selected


def format_news_section_text() -> str:
    lines = ["当日新闻："]
    seen_titles = set()

    for category_config in NEWS_CATEGORY_CONFIGS:
        category_name = category_config["name"]
        items = collect_category_items(category_config, seen_titles)

        lines.append(f"【{category_name}】")
        if not items:
            lines.append("- 暂无高相关更新")
            continue

        for item in items:
            translated_title = translate_text_to_zh(item["title"])
            time_text = format_news_time(item["published_at"])
            meta = item["source"]
            if time_text:
                meta = f"{meta}，{time_text}"
            lines.append(f"- {translated_title}（{meta}）")
            if item.get("url"):
                lines.append(f"  链接：{item['url']}")

    return "\n".join(lines)


def format_daily_report_text() -> str:
    dt, current = get_copenhagen_now()
    date_str = dt.strftime("%Y-%m-%d")
    time_str = dt.strftime("%H:%M")
    temp = current.get("temperature_2m")
    weather_code = current.get("weather_code")
    wind_speed = current.get("wind_speed_10m")
    holiday_text = get_holiday_text(date_str)
    life_section = format_student_life_section_text(dt)
    news_section = format_news_section_text()

    base_text = (
        f"哥本哈根每日播报\n"
        f"时间：{date_str} {time_str}\n"
        f"天气：{weather_code_to_text(weather_code)}\n"
        f"温度：{temp}°C\n"
        f"风速：{wind_speed} km/h\n"
        f"今天是否为丹麦公共假期：{holiday_text}"
    )
    sections = [base_text]
    if life_section:
        sections.append(life_section)
    sections.append(news_section)
    return "\n\n".join(sections)


def get_copenhagen_status() -> str:
    return format_daily_report_text()


def split_wecom_text(content: str) -> list[str]:
    if len(content) <= WECOM_TEXT_MAX_CHARS:
        return [content]

    chunk_limit = max(100, WECOM_TEXT_MAX_CHARS - 16)
    chunks = []
    current_lines = []
    current_length = 0

    for line in content.splitlines():
        line_length = len(line) + 1
        if current_lines and current_length + line_length > chunk_limit:
            chunks.append("\n".join(current_lines))
            current_lines = []
            current_length = 0

        if line_length > chunk_limit:
            for start in range(0, len(line), chunk_limit):
                part = line[start : start + chunk_limit]
                if current_lines:
                    chunks.append("\n".join(current_lines))
                    current_lines = []
                    current_length = 0
                chunks.append(part)
            continue

        current_lines.append(line)
        current_length += line_length

    if current_lines:
        chunks.append("\n".join(current_lines))

    if len(chunks) <= 1:
        return chunks

    return [f"({index + 1}/{len(chunks)})\n{chunk}" for index, chunk in enumerate(chunks)]


def send_wecom_text(content: str) -> dict:
    chunks = split_wecom_text(content)
    webhook_url = build_wecom_webhook_url()
    if webhook_url:
        result = {}
        for chunk in chunks:
            result = send_wecom_webhook_text(chunk, webhook_url)
        return result

    if not WECOM_AGENT_ID or not WECOM_TOUSER:
        raise ValueError("缺少 WECOM_AGENT_ID 或 WECOM_TOUSER")

    access_token = get_access_token()
    url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={access_token}"
    result = {}

    for chunk in chunks:
        payload = {
            "touser": WECOM_TOUSER,
            "msgtype": "text",
            "agentid": int(WECOM_AGENT_ID),
            "text": {"content": chunk},
            "safe": 0,
        }

        resp = requests.post(url, json=payload, headers=REQUEST_HEADERS, timeout=HTTP_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()

        if data.get("errcode") != 0:
            raise ValueError(f"发送企业微信消息失败: {data}")

        result = data

    return result


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
