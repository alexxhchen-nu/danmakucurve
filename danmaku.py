"""抓弹幕 + 解析弹幕 XML。

B 站公开接口，不用登录：
  1. https://api.bilibili.com/x/player/pagelist?bvid=BV...      -> 拿 cid
  2. https://api.bilibili.com/x/v1/dm/list.so?oid=<cid>         -> 弹幕 XML（最多约 1000 条）
"""
import re
import xml.etree.ElementTree as ET

UA = "Mozilla/5.0 (DanmakuCurve research script)"


def bvid_from_url(url_or_bvid):
    m = re.search(r"(BV[0-9A-Za-z]{10})", url_or_bvid)
    if not m:
        raise ValueError(f"没找到 BV 号: {url_or_bvid}")
    return m.group(1)


def _decode(raw):
    """把接口返回的字节变成文字。不看响应头，按内容逐个试：
    未压缩、gzip、zlib、不带头的 deflate、brotli。哪个能解成 UTF-8 就用哪个。"""
    import gzip
    import zlib

    tries = [
        lambda b: b,
        gzip.decompress,
        zlib.decompress,
        lambda b: zlib.decompress(b, -zlib.MAX_WBITS),
    ]
    try:
        import brotli
        tries.append(brotli.decompress)
    except ImportError:
        pass
    for f in tries:
        try:
            return f(raw).decode("utf-8")
        except Exception:
            continue
    raise ValueError(f"接口返回的内容解不开（开头几个字节: {raw[:8]!r}）")


def _get_text(url, params, timeout):
    """B 站弹幕接口常返回压缩过的内容，而且响应头不一定写对，所以拿原始字节自己解。"""
    import requests

    headers = {
        "User-Agent": UA,
        "Referer": "https://www.bilibili.com/",
        "Accept-Encoding": "gzip, deflate",
    }
    r = requests.get(url, params=params, headers=headers, timeout=timeout, stream=True)
    r.raise_for_status()
    return _decode(r.raw.read(decode_content=False))


def fetch_xml(url_or_bvid, page=1, timeout=15):
    """返回 (title, xml_text)。需要能连上 api.bilibili.com。"""
    import json

    bvid = bvid_from_url(url_or_bvid)
    data = json.loads(_get_text("https://api.bilibili.com/x/player/pagelist", {"bvid": bvid}, timeout))
    if data.get("code") != 0:
        raise RuntimeError(f"B 站返回错误: {data.get('message')}")
    part = data["data"][page - 1]
    cid = part["cid"]
    title = part.get("part") or bvid
    try:  # 视频标题，拿不到就用分 P 名
        view = json.loads(_get_text("https://api.bilibili.com/x/web-interface/view", {"bvid": bvid}, timeout))
        title = view["data"]["title"] or title
    except Exception:
        pass
    return title, _get_text("https://api.bilibili.com/x/v1/dm/list.so", {"oid": cid}, timeout)


def parse_xml(xml_text):
    """弹幕 XML -> [(视频秒数, 文本)]，按时间排序。"""
    root = ET.fromstring(xml_text.encode("utf-8") if isinstance(xml_text, str) else xml_text)
    rows = []
    for d in root.iter("d"):
        p = d.get("p", "")
        text = (d.text or "").strip()
        if not p or not text:
            continue
        rows.append((float(p.split(",")[0]), text))
    rows.sort(key=lambda r: r[0])
    return rows
