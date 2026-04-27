import html
import json
import os
import re
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import quote, urlencode
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
ETILBUDSAVIS_SEARCH_URL = "https://etilbudsavis.dk/soeg/{query}"
MINETILBUD_URL = "https://minetilbud.dk/"
MATAS_HAND_SANITIZER_URL = "https://www.matas.dk/medicin-pleje/saarpleje/haandsprit"
UNGDOMSKORT_URL = "https://ungdomskort.dk/english"
DSB_ORANGE_URL = "https://www.dsb.dk/en/find-produkter-og-services/orange/"
DSB_ORANGE_FRI_URL = "https://www.dsb.dk/en/tickets-and-services/orange-fri/"
REJSEKORT_IMPORTANT_DATES_URL = "https://www.rejsekort.dk/en/luk/Vigtige-datoer/Vigtige-datoer"
REJSEPLANEN_APP_URL = "https://help.rejseplanen.dk/hc/en-us/articles/115002672449-Rejseplanen-s-app"
TEQUILA_SEARCH_URL = "https://tequila-api.kiwi.com/v2/search"
GOOGLE_FLIGHTS_URL = "https://www.google.com/travel/flights"
TRAVELPAYOUTS_PRICES_FOR_DATES_URL = (
    "https://api.travelpayouts.com/aviasales/v3/prices_for_dates"
)

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
LIFE_DEAL_ITEMS_PER_QUERY = int(os.getenv("LIFE_DEAL_ITEMS_PER_QUERY", "1"))
LIFE_MAX_DEAL_ITEMS = int(os.getenv("LIFE_MAX_DEAL_ITEMS", "6"))
LIFE_PRODUCT_QUERIES_TEXT = os.getenv(
    "LIFE_PRODUCT_QUERIES",
    (
        "håndsprit:消毒/免洗洗手液;"
        "vaskemiddel:洗衣液;"
        "toiletpapir:厕纸/纸巾;"
        "opvaskemiddel:洗洁精;"
        "rugbrød:黑麦面包;"
        "brød:面包"
    ),
)
WECOM_TEXT_MAX_CHARS = int(os.getenv("WECOM_TEXT_MAX_CHARS", "1800"))
FLIGHT_WATCH_ENABLED = os.getenv("FLIGHT_WATCH_ENABLED", "1").lower() not in {
    "0",
    "false",
    "no",
    "off",
}
TEQUILA_API_KEY = os.getenv("TEQUILA_API_KEY", "")
TRAVELPAYOUTS_TOKEN = os.getenv("TRAVELPAYOUTS_TOKEN", "")
FLIGHT_ORIGINS_TEXT = os.getenv("FLIGHT_ORIGINS", "CAN:广州;SZX:深圳;HKG:香港")
FLIGHT_DESTINATION_TEXT = os.getenv("FLIGHT_DESTINATION", "DXB:迪拜")
FLIGHT_DEPARTURE_FROM = os.getenv("FLIGHT_DEPARTURE_FROM", "2026-07-25")
FLIGHT_DEPARTURE_TO = os.getenv("FLIGHT_DEPARTURE_TO", "2026-08-08")
FLIGHT_STAY_NIGHTS = int(os.getenv("FLIGHT_STAY_NIGHTS", "4"))
FLIGHT_MAX_RESULTS = int(os.getenv("FLIGHT_MAX_RESULTS", "5"))
FLIGHT_CURRENCY = os.getenv("FLIGHT_CURRENCY", "CNY")

KU_PHARMACY_CAMPUS = {
    "name": "KU 药学院 / Department of Pharmacy",
    "address": "Dyrlægevej 100, 1870 Frederiksberg C",
    "reception_address": "Dyrlægevej 100, 1870 Frederiksberg C",
    "nearby_bus_lines": [],
}

STUDENT_HOME = {
    "name": "Valby 租房",
    "address": "Skyttegårdvej 9, 2500 Valby",
}

DAILY_ROUTE = {
    "summary": f"{STUDENT_HOME['address']} ↔ {KU_PHARMACY_CAMPUS['address']}",
    "areas": ["Valby", "Frederiksberg"],
}

ROUTE_STORE_RULES = [
    {
        "keywords": ["rema 1000", "netto", "lidl", "føtex", "foetex", "matas", "normal"],
        "level": "route",
        "note": "日常高频店，适合在 Valby/KU/通勤路线上顺手确认",
        "score": 0,
    },
    {
        "keywords": ["bilka", "meny", "365discount", "365 discount", "coop"],
        "level": "maybe",
        "note": "可能有用，但先确认是否顺路",
        "score": 1,
    },
    {
        "keywords": ["biltema", "calle", "nielsen scan-shop", "scandinavian park"],
        "level": "skip",
        "note": "通常不在 Valby ↔ KU 两点一线，不建议专门去",
        "score": 3,
    },
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


def parse_life_product_queries(raw_text: str) -> list[dict]:
    queries = []
    for part in re.split(r"[;\n]+", raw_text):
        normalized = part.strip()
        if not normalized:
            continue

        if ":" in normalized:
            query, label = normalized.split(":", 1)
        elif "=" in normalized:
            query, label = normalized.split("=", 1)
        else:
            query, label = normalized, normalized

        query = query.strip()
        label = label.strip() or query
        if query:
            queries.append({"query": query, "label": label})

    return queries


def parse_labeled_code_list(raw_text: str) -> list[dict]:
    items = []
    for item in parse_life_product_queries(raw_text):
        code = item["query"].upper()
        items.append({"code": code, "label": item["label"] or code})
    return items


def parse_destination(raw_text: str) -> dict:
    items = parse_labeled_code_list(raw_text)
    if items:
        return items[0]
    return {"code": "DXB", "label": "迪拜"}


def build_maps_search_url(query: str) -> str:
    params = {"api": "1", "query": query}
    return f"https://www.google.com/maps/search/?{urlencode(params)}"


def build_etilbudsavis_search_url(query: str) -> str:
    query_slug = quote(query.replace(" ", "-"), safe="")
    return ETILBUDSAVIS_SEARCH_URL.format(query=query_slug)


def parse_dkk_price(price_text: str) -> float:
    number_match = re.search(r"\d[\d.,]*", price_text)
    if not number_match:
        return 10**9

    value = number_match.group(0)
    if "." in value and "," in value:
        if value.rfind(",") > value.rfind("."):
            value = value.replace(".", "").replace(",", ".")
        else:
            value = value.replace(",", "")
    elif "," in value:
        value = value.replace(".", "").replace(",", ".")
    elif "." in value:
        parts = value.split(".")
        if len(parts[-1]) == 3 and len(parts) > 1:
            value = value.replace(".", "")

    try:
        return float(value)
    except ValueError:
        return 10**9


def format_dkk_price(value) -> str:
    if value is None:
        return ""
    if isinstance(value, (int, float)):
        if float(value).is_integer():
            return f"{int(value)} kr"
        return f"{float(value):.2f}".replace(".", ",") + " kr"
    text = str(value).strip()
    if not text:
        return ""
    if "kr" in text.lower():
        return text
    return f"{text} kr"


def parse_offer_datetime(value: str) -> datetime | None:
    if not value:
        return None

    normalized = value.strip().replace("Z", "+00:00")
    if re.search(r"[+-]\d{4}$", normalized):
        normalized = f"{normalized[:-5]}{normalized[-5:-2]}:{normalized[-2:]}"

    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None

    if parsed.tzinfo:
        return parsed.astimezone(LOCAL_NEWS_TZ)
    return parsed.replace(tzinfo=LOCAL_NEWS_TZ)


def format_offer_valid_until(valid_until: datetime | None) -> str:
    if not valid_until:
        return ""
    return valid_until.strftime("%m-%d")


def safe_float(value) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


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


def extract_embedded_json_objects(page_text: str) -> list[dict]:
    normalized_text = html.unescape(page_text)
    decoder = json.JSONDecoder()
    objects = []

    json_ld_scripts = re.findall(
        r"<script[^>]+type=[\"']application/ld\+json[\"'][^>]*>(.*?)</script>",
        normalized_text,
        flags=re.I | re.S,
    )
    for script in json_ld_scripts:
        try:
            obj = json.loads(script.strip())
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            objects.append(obj)
        elif isinstance(obj, list):
            objects.extend(item for item in obj if isinstance(item, dict))

    search_start = 0

    while True:
        start = normalized_text.find('{"data"', search_start)
        if start < 0:
            break

        try:
            obj, end = decoder.raw_decode(normalized_text[start:])
        except json.JSONDecodeError:
            search_start = start + 1
            continue

        if isinstance(obj, dict):
            objects.append(obj)
        search_start = start + end

    return objects


def normalize_offer_item(raw_item: dict, label: str, query: str, source_url: str) -> dict | None:
    if not isinstance(raw_item, dict):
        return None

    name = (
        raw_item.get("heading")
        or raw_item.get("name")
        or raw_item.get("title")
        or raw_item.get("description")
        or ""
    )
    name = clean_html_text(str(name))
    if not name:
        return None

    pricing = raw_item.get("pricing") or {}
    if not isinstance(pricing, dict):
        pricing = {}
    price = (
        raw_item.get("price")
        or pricing.get("price")
        or pricing.get("amount")
        or raw_item.get("offerPrice")
        or raw_item.get("currentPrice")
        or ""
    )
    price_text = format_dkk_price(price)
    if not price_text:
        return None

    shop = (
        raw_item.get("business")
        or raw_item.get("store")
        or raw_item.get("dealer")
        or raw_item.get("seller")
        or {}
    )
    if isinstance(shop, dict):
        shop_name = shop.get("name") or shop.get("title") or ""
    else:
        shop_name = str(shop)
    shop_name = clean_html_text(shop_name) or "eTilbudsavis"

    valid_until = parse_offer_datetime(
        str(
            raw_item.get("validUntil")
            or raw_item.get("validTo")
            or raw_item.get("validTill")
            or raw_item.get("runTill")
            or raw_item.get("priceValidUntil")
            or raw_item.get("validThrough")
            or ""
        )
    )
    now = datetime.now(LOCAL_NEWS_TZ)
    if valid_until and valid_until < now:
        return None

    return {
        "label": label,
        "query": query,
        "name": name,
        "price": price_text,
        "price_value": parse_dkk_price(price_text),
        "shop": shop_name,
        "valid_until": valid_until,
        "url": raw_item.get("url") or source_url,
    }


def collect_offer_items_from_json(
    obj,
    label: str,
    query: str,
    source_url: str,
) -> list[dict]:
    offers = []
    if isinstance(obj, list):
        for item in obj:
            offers.extend(collect_offer_items_from_json(item, label, query, source_url))
        return offers

    if not isinstance(obj, dict):
        return offers

    normalized_offer = normalize_offer_item(obj, label, query, source_url)
    if normalized_offer:
        offers.append(normalized_offer)

    for value in obj.values():
        if isinstance(value, (dict, list)):
            offers.extend(collect_offer_items_from_json(value, label, query, source_url))

    return offers


def fetch_etilbudsavis_offer_items(query: str, label: str, limit: int) -> list[dict]:
    search_url = build_etilbudsavis_search_url(query)
    try:
        resp = requests.get(search_url, headers=REQUEST_HEADERS, timeout=HTTP_TIMEOUT)
        resp.raise_for_status()
    except requests.RequestException:
        return []

    offers = []
    for obj in extract_embedded_json_objects(resp.text):
        offers.extend(collect_offer_items_from_json(obj, label, query, search_url))

    unique_offers = []
    seen = set()
    for offer in sorted(
        offers,
        key=lambda item: (item["price_value"], item["shop"], item["name"]),
    ):
        key = normalize_title(
            f"{offer['label']} {offer['shop']} {offer['name']} {offer['price']}"
        )
        if key in seen:
            continue
        seen.add(key)
        unique_offers.append(offer)
        if len(unique_offers) >= limit:
            break

    return unique_offers


def fetch_matas_hand_sanitizer_deals(label: str, limit: int) -> list[dict]:
    deals = []
    for item in fetch_matas_hand_sanitizer_examples(limit):
        deals.append(
            {
                "label": label,
                "query": "håndsprit",
                "name": item["name"],
                "price": item["price"],
                "price_value": parse_dkk_price(item["price"]),
                "shop": item["source"],
                "valid_until": None,
                "url": item["url"],
            }
        )
    return deals


def collect_life_deal_items() -> tuple[list[dict], list[dict]]:
    product_queries = parse_life_product_queries(LIFE_PRODUCT_QUERIES_TEXT)
    deal_items = []

    for config in product_queries:
        query = config["query"]
        label = config["label"]
        items = fetch_etilbudsavis_offer_items(query, label, LIFE_DEAL_ITEMS_PER_QUERY)

        if not items and contains_any_keyword(
            query.lower(),
            ["håndsprit", "haandsprit", "desinfektion"],
        ):
            items = fetch_matas_hand_sanitizer_deals(label, LIFE_DEAL_ITEMS_PER_QUERY)

        deal_items.extend(items)
        if len(deal_items) >= LIFE_MAX_DEAL_ITEMS:
            break

    return deal_items[:LIFE_MAX_DEAL_ITEMS], product_queries


def format_life_deal_item(item: dict) -> str:
    valid_text = format_offer_valid_until(item.get("valid_until"))
    route_info = classify_store_for_route(item.get("shop", ""))
    meta_parts = [item["shop"], item["price"]]
    if valid_text:
        meta_parts.append(f"至 {valid_text}")
    if route_info["level"] == "skip":
        meta_parts.append("不建议专门去")
    elif route_info["level"] == "route":
        meta_parts.append("可顺路确认")
    return f"- {item['label']}：{item['name']}（{'，'.join(meta_parts)}）"


def classify_store_for_route(shop_name: str) -> dict:
    normalized = normalize_title(shop_name)
    for rule in ROUTE_STORE_RULES:
        if any(keyword in normalized for keyword in rule["keywords"]):
            return rule
    return {
        "level": "unknown",
        "note": "未确认是否在 Valby ↔ KU 两点一线，先看链接再决定",
        "score": 2,
    }


def actionability_score(item: dict) -> tuple[int, float, str]:
    route_info = classify_store_for_route(item.get("shop", ""))
    return (
        route_info["score"],
        item.get("price_value", 10**9),
        normalize_title(item.get("label", "")),
    )


def select_route_worthy_deals(deal_items: list[dict], limit: int = 2) -> list[dict]:
    candidates = [
        item
        for item in deal_items
        if classify_store_for_route(item.get("shop", ""))["level"] in {"route", "maybe"}
    ]
    return sorted(candidates, key=actionability_score)[:limit]


def select_skip_deals(deal_items: list[dict], limit: int = 2) -> list[dict]:
    candidates = [
        item
        for item in deal_items
        if classify_store_for_route(item.get("shop", ""))["level"] == "skip"
    ]
    return sorted(candidates, key=actionability_score)[:limit]


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


def build_weather_decision(current: dict) -> str:
    temp = safe_float(current.get("temperature_2m"))
    wind_speed = safe_float(current.get("wind_speed_10m"))
    weather_code = current.get("weather_code")
    weather_text = weather_code_to_text(weather_code)

    clothing_parts = []
    if temp is None:
        clothing_parts.append("按体感备外套")
    elif temp < 5:
        clothing_parts.append("很冷，羽绒/厚外套和围巾更稳")
    elif temp < 12:
        clothing_parts.append("早晚偏冷，带外套")
    elif temp < 18:
        clothing_parts.append("薄外套够用")
    else:
        clothing_parts.append("穿轻便一点即可")

    if weather_code in {51, 53, 55, 61, 63, 65, 80, 81, 82, 95}:
        clothing_parts.append("带伞或防水外套")
    if wind_speed is not None and wind_speed >= 25:
        clothing_parts.append("风大，骑车注意")

    return f"天气{weather_text}，{format_temperature_for_advice(temp)}；{'，'.join(clothing_parts)}。"


def format_temperature_for_advice(temp: float | None) -> str:
    if temp is None:
        return "温度未知"
    return f"{temp:g}°C"


def build_holiday_decision(holiday_text: str) -> str:
    if holiday_text.startswith("是"):
        return f"今天是丹麦公共假期（{holiday_text.removeprefix('是，')}），出门前确认超市/药店营业时间。"
    return "今天不是丹麦公共假期，学校、超市和药店大概率正常营业。"


def build_procurement_decision(deal_items: list[dict]) -> str:
    route_worthy_deals = select_route_worthy_deals(deal_items)
    skip_deals = select_skip_deals(deal_items)

    if not route_worthy_deals:
        if skip_deals:
            ignored = "、".join(
                f"{item['label']}({item['shop']})" for item in skip_deals
            )
            return (
                "今天不建议专门采购；抓到的低价主要不在 Valby ↔ KU 两点一线，"
                f"例如 {ignored}，除非本来要路过。"
            )
        return "今天不建议专门采购；暂时没有抓到明显值得顺路买的生活用品。"

    first_deal = route_worthy_deals[0]
    extra = ""
    if len(route_worthy_deals) > 1:
        other_labels = "、".join(item["label"] for item in route_worthy_deals[1:])
        extra = f"；同店/同路线还可看 {other_labels}"

    return (
        f"今天不需要大采购；如果路过 {first_deal['shop']}，"
        f"可顺手看 {first_deal['label']}（{first_deal['price']}）{extra}。"
    )


def build_food_decision(now: datetime) -> str:
    if now.hour < 17:
        time_hint = "晚上 18:30 后"
    elif now.hour < 21:
        time_hint = "现在到关门前"
    else:
        time_hint = "明晚 18:30 后"

    return (
        f"{time_hint}可以刷 Too Good To Go；优先看 Valby 住处附近和 KU/Frederiksberg "
        "附近面包店，不为便宜专门跨城。"
    )


def build_wellbeing_decision(now: datetime, current: dict) -> str:
    temp = safe_float(current.get("temperature_2m"))
    weather_code = current.get("weather_code")
    is_rainy = weather_code in {51, 53, 55, 61, 63, 65, 80, 81, 82, 95}
    is_weekend = now.weekday() >= 5

    if is_rainy or (temp is not None and temp < 4):
        return (
            "今天适合安排一个低成本室内出口：KU 图书馆、学校自习区，"
            "或回 Valby 后做一顿热饭，别把晚上完全留给刷手机。"
        )
    if is_weekend:
        return (
            "今天适合低成本换环境：Frederiksberg Have / Søndermarken / Valbyparken "
            "任选一个散步 30-60 分钟，缓解无聊和孤独感。"
        )
    return (
        "课后如果还有精力，建议在回 Valby 前顺路散步 20 分钟或逛一次常去超市；"
        "目标是换环境，不是强行消费。"
    )


def build_transport_decision(now: datetime) -> str:
    rejsekort_close_date = datetime(2026, 5, 29, tzinfo=now.tzinfo).date()
    days_left = (rejsekort_close_date - now.date()).days
    if days_left >= 0:
        return (
            f"本周提醒：实体 Rejsekort 系统 2026-05-29 关闭，还剩 {days_left} 天；"
            "如果还在用旧卡，别留太多余额，优先迁到 Rejsekort app。"
        )
    return "交通提醒：实体 Rejsekort 系统已关闭，日常优先使用 Rejsekort app / Rejsebillet。"


def format_daily_advice_section(
    now: datetime,
    current: dict,
    holiday_text: str,
    deal_items: list[dict],
) -> list[str]:
    advice_items = [
        build_weather_decision(current),
        build_holiday_decision(holiday_text),
        build_procurement_decision(deal_items),
        build_food_decision(now),
        build_wellbeing_decision(now, current),
        build_transport_decision(now),
    ]

    lines = [
        "今日建议：",
        f"活动范围：{DAILY_ROUTE['summary']}",
    ]
    lines.extend(f"{index}. {text}" for index, text in enumerate(advice_items, 1))
    return lines


def format_campus_life_header() -> list[str]:
    bus_hint = (
        f"；公交关注 {'/'.join(KU_PHARMACY_CAMPUS['nearby_bus_lines'])}"
        if KU_PHARMACY_CAMPUS["nearby_bus_lines"]
        else "；通勤路线以 Rejseplanen 当天结果为准"
    )
    return [
        "生活参考（按 Valby ↔ KU 两点一线筛选）：",
        (
            f"学校：{KU_PHARMACY_CAMPUS['address']}；住处：{STUDENT_HOME['address']}"
            f"{bus_hint}"
        ),
    ]


def format_bakery_discount_section() -> list[str]:
    campus_query = f"bakery near {KU_PHARMACY_CAMPUS['address']}"
    return [
        "【面包/临期食品】",
        (
            "- Too Good To Go：把位置设为 Dyrlægevej 100 或 Valby 住处，收藏 "
            "Frederiksberg / Valby 面包店和咖啡店，晚间/关门前更容易刷到 surprise bag。"
        ),
        f"  入口：{TOO_GOOD_TO_GO_URL}",
        f"  地图查附近面包店：{build_maps_search_url(campus_query)}",
    ]


def format_life_goods_section(
    deal_items: list[dict] | None = None,
    product_queries: list[dict] | None = None,
) -> list[str]:
    lines = ["【生活用品实时优惠】"]
    if deal_items is None or product_queries is None:
        deal_items, product_queries = collect_life_deal_items()

    if deal_items:
        for item in deal_items:
            lines.append(format_life_deal_item(item))
            lines.append(f"  链接：{item['url']}")
    else:
        lines.append("- 暂未抓到当前有效优惠；下面保留实时搜索入口。")

    top_searches = fetch_etilbudsavis_top_searches(12)
    tracked_queries = {normalize_title(config["query"]) for config in product_queries}
    relevant_searches = [
        title for title in top_searches if normalize_title(title) in tracked_queries
    ]
    if relevant_searches:
        lines.append(f"- eTilbudsavis 近期热搜匹配：{' / '.join(relevant_searches[:4])}")

    tracked_labels = "、".join(
        f"{config['label']}({config['query']})" for config in product_queries
    )
    lines.append(f"- 当前关注词：{tracked_labels}")
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
        "- 上学通勤：先用 Rejseplanen 算住址到 Dyrlægevej 100 的区数；"
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


def format_tequila_date(date_str: str) -> str:
    dt = datetime.fromisoformat(date_str)
    return dt.strftime("%d/%m/%Y")


def parse_datetime_safe(value: str) -> datetime | None:
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


def format_flight_date(value: str) -> str:
    dt = parse_datetime_safe(value)
    if not dt:
        return ""
    return dt.strftime("%m-%d %H:%M")


def build_flight_search_url(origin: dict, destination: dict) -> str:
    return build_flight_search_url_for_dates(
        origin,
        destination,
        datetime.fromisoformat(FLIGHT_DEPARTURE_FROM).date(),
    )


def build_flight_search_url_for_dates(origin: dict, destination: dict, departure_date) -> str:
    return_date = departure_date + timedelta(days=FLIGHT_STAY_NIGHTS)
    query = (
        f"{origin['code']} to {destination['code']} direct flights "
        f"{departure_date.strftime('%Y-%m-%d')} return {return_date.strftime('%Y-%m-%d')}"
    )
    return f"{GOOGLE_FLIGHTS_URL}?{urlencode({'q': query})}"


def iter_flight_departure_dates():
    current = datetime.fromisoformat(FLIGHT_DEPARTURE_FROM).date()
    end = datetime.fromisoformat(FLIGHT_DEPARTURE_TO).date()
    while current <= end:
        yield current
        current += timedelta(days=1)


def normalize_travelpayouts_flight_item(
    item: dict,
    origin: dict,
    destination: dict,
    departure_date,
) -> dict | None:
    price = item.get("price") or item.get("value")
    if price is None:
        return None

    departure = item.get("departure_at") or departure_date.isoformat()
    return_departure = item.get("return_at") or (
        departure_date + timedelta(days=FLIGHT_STAY_NIGHTS)
    ).isoformat()
    airline = item.get("airline") or item.get("airline_code") or "未知航司"

    return {
        "origin": origin,
        "destination": destination,
        "price": price,
        "price_value": parse_dkk_price(str(price)),
        "currency": FLIGHT_CURRENCY,
        "departure": departure,
        "return_departure": return_departure,
        "nights": FLIGHT_STAY_NIGHTS,
        "departure_date": departure_date.isoformat(),
        "return_date": (departure_date + timedelta(days=FLIGHT_STAY_NIGHTS)).isoformat(),
        "airlines": airline,
        "booking_url": build_flight_search_url_for_dates(origin, destination, departure_date),
        "provider": "Travelpayouts/Aviasales 缓存价",
    }


def fetch_travelpayouts_direct_flight_offer(
    origin: dict,
    destination: dict,
    departure_date,
) -> dict | None:
    if not TRAVELPAYOUTS_TOKEN:
        return None

    return_date = departure_date + timedelta(days=FLIGHT_STAY_NIGHTS)
    params = {
        "origin": origin["code"],
        "destination": destination["code"],
        "departure_at": departure_date.isoformat(),
        "return_at": return_date.isoformat(),
        "currency": FLIGHT_CURRENCY.lower(),
        "sorting": "price",
        "direct": "true",
        "one_way": "false",
        "limit": 1,
        "token": TRAVELPAYOUTS_TOKEN,
    }

    try:
        resp = requests.get(
            TRAVELPAYOUTS_PRICES_FOR_DATES_URL,
            params=params,
            headers=REQUEST_HEADERS,
            timeout=HTTP_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException:
        return None
    except ValueError:
        return None

    offers = data.get("data") or []
    for item in offers:
        normalized = normalize_travelpayouts_flight_item(
            item,
            origin,
            destination,
            departure_date,
        )
        if normalized:
            return normalized
    return None


def fetch_travelpayouts_direct_flight_deals_for_origin(
    origin: dict,
    destination: dict,
) -> list[dict]:
    deals = []
    for departure_date in iter_flight_departure_dates():
        offer = fetch_travelpayouts_direct_flight_offer(
            origin,
            destination,
            departure_date,
        )
        if offer:
            deals.append(offer)
    return deals


def find_return_departure(route: list[dict], destination_code: str) -> str:
    for segment in route:
        if segment.get("return") == 1:
            return segment.get("local_departure", "")
    for segment in route:
        if segment.get("flyFrom") == destination_code:
            return segment.get("local_departure", "")
    return ""


def normalize_flight_item(item: dict, origin: dict, destination: dict) -> dict:
    route = item.get("route") or []
    return_departure = find_return_departure(route, destination["code"])
    airlines = item.get("airlines") or []
    return {
        "origin": origin,
        "destination": destination,
        "price": item.get("price"),
        "currency": FLIGHT_CURRENCY,
        "departure": item.get("local_departure", ""),
        "return_departure": return_departure,
        "nights": item.get("nightsInDest") or FLIGHT_STAY_NIGHTS,
        "airlines": "/".join(airlines) if airlines else "未知航司",
        "booking_url": item.get("deep_link", ""),
        "provider": "Kiwi Tequila",
    }


def fetch_direct_flight_deals_for_origin(origin: dict, destination: dict) -> list[dict]:
    if not TEQUILA_API_KEY:
        return []

    params = {
        "fly_from": origin["code"],
        "fly_to": destination["code"],
        "date_from": format_tequila_date(FLIGHT_DEPARTURE_FROM),
        "date_to": format_tequila_date(FLIGHT_DEPARTURE_TO),
        "nights_in_dst_from": FLIGHT_STAY_NIGHTS,
        "nights_in_dst_to": FLIGHT_STAY_NIGHTS,
        "flight_type": "round",
        "max_stopovers": 0,
        "curr": FLIGHT_CURRENCY,
        "limit": FLIGHT_MAX_RESULTS,
        "sort": "price",
        "vehicle_type": "aircraft",
    }
    headers = {"apikey": TEQUILA_API_KEY}

    try:
        resp = requests.get(
            TEQUILA_SEARCH_URL,
            params=params,
            headers=headers | REQUEST_HEADERS,
            timeout=HTTP_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException:
        return []
    except ValueError:
        return []

    return [
        normalize_flight_item(item, origin, destination)
        for item in data.get("data", [])
        if item.get("price") is not None
    ]


def collect_direct_flight_deals() -> tuple[list[dict], list[dict], dict]:
    origins = parse_labeled_code_list(FLIGHT_ORIGINS_TEXT)
    destination = parse_destination(FLIGHT_DESTINATION_TEXT)
    deals = []

    if TRAVELPAYOUTS_TOKEN:
        for origin in origins:
            deals.extend(fetch_travelpayouts_direct_flight_deals_for_origin(origin, destination))
    elif TEQUILA_API_KEY:
        for origin in origins:
            deals.extend(fetch_direct_flight_deals_for_origin(origin, destination))

    deals.sort(
        key=lambda item: item.get(
            "price_value",
            parse_dkk_price(str(item.get("price", ""))),
        )
    )
    return deals[:FLIGHT_MAX_RESULTS], origins, destination


def format_flight_deal(item: dict) -> str:
    departure = format_flight_date(item["departure"]) or "日期未知"
    return_departure = format_flight_date(item["return_departure"]) or "返程未知"
    price_text = f"{item['price']} {item['currency']}"
    provider_text = f"，{item['provider']}" if item.get("provider") else ""
    return (
        f"- {item['origin']['label']}({item['origin']['code']}) → "
        f"{item['destination']['label']}({item['destination']['code']})："
        f"{price_text}，{departure} 出发，{return_departure} 返程，"
        f"{item['nights']}晚，{item['airlines']}{provider_text}"
    )


def format_flight_watch_section_text() -> str:
    if not FLIGHT_WATCH_ENABLED:
        return ""

    deals, origins, destination = collect_direct_flight_deals()
    route_text = " / ".join(f"{origin['label']}({origin['code']})" for origin in origins)
    lines = [
        "直飞迪拜低价航班观察：",
        (
            f"规则：枚举 {FLIGHT_DEPARTURE_FROM} 至 {FLIGHT_DEPARTURE_TO} 的每个出发日，"
            f"返程固定 +{FLIGHT_STAY_NIGHTS}晚；{route_text} → "
            f"{destination['label']}({destination['code']})；仅直飞；按价格排序。"
        ),
    ]

    if (
        not TRAVELPAYOUTS_TOKEN
        and not TEQUILA_API_KEY
    ):
        lines.append(
            "- 未配置免费航班 API 凭证，暂不自动记录实时价格；"
            "推荐配置 TRAVELPAYOUTS_TOKEN 后使用 Aviasales 缓存价自动筛选最低价。"
        )
        for origin in origins:
            lines.append(
                f"  {origin['label']}({origin['code']}) 查询："
                f"{build_flight_search_url(origin, destination)}"
            )
        return "\n".join(lines)

    if not deals:
        if TRAVELPAYOUTS_TOKEN:
            provider_hint = "Travelpayouts/Aviasales 缓存价"
        else:
            provider_hint = "Kiwi Tequila"
        lines.append(
            f"- {provider_hint} 暂未抓到符合条件的直飞低价结果；"
            "建议放宽日期，或同步查 DWC。"
        )
        for origin in origins:
            lines.append(
                f"  {origin['label']}({origin['code']}) 手动查："
                f"{build_flight_search_url(origin, destination)}"
            )
        return "\n".join(lines)

    lines.append("当前低价：")
    for item in deals:
        lines.append(format_flight_deal(item))
        if item.get("booking_url"):
            lines.append(f"  链接：{item['booking_url']}")
    return "\n".join(lines)


def format_student_life_section_text(
    now: datetime,
    current: dict,
    holiday_text: str,
) -> str:
    if not LIFE_INFO_ENABLED:
        return ""

    deal_items, product_queries = collect_life_deal_items()
    lines = []
    lines.extend(format_daily_advice_section(now, current, holiday_text, deal_items))
    lines.append("")
    lines.extend(format_campus_life_header())
    lines.extend(format_bakery_discount_section())
    lines.extend(format_life_goods_section(deal_items, product_queries))
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
    life_section = format_student_life_section_text(dt, current, holiday_text)
    flight_section = format_flight_watch_section_text()

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
    if flight_section:
        sections.append(flight_section)
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
