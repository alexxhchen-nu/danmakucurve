"""抓弹幕的解压：不管 B 站用哪种压缩、响应头写没写，都要能读出 XML。不连网。"""
import gzip
import os
import sys
import zlib

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from danmaku import _decode, parse_xml  # noqa: E402

HERE = os.path.dirname(__file__)
XML = open(os.path.join(HERE, "..", "data", "sample_BV1YNZvYzELw.xml"), encoding="utf-8").read()


def _raw_deflate(b):
    c = zlib.compressobj(9, zlib.DEFLATED, -zlib.MAX_WBITS)
    return c.compress(b) + c.flush()


def test_all_encodings():
    b = XML.encode("utf-8")
    for name, data in [("plain", b), ("gzip", gzip.compress(b)), ("zlib", zlib.compress(b)),
                       ("raw deflate", _raw_deflate(b))]:
        text = _decode(data)
        assert text == XML, name
        assert len(parse_xml(text)) == 332, name


def test_garbage_raises():
    try:
        _decode(b"\xfd\x00\xff\xfe\x01not-anything")
    except ValueError:
        return
    raise AssertionError("应该报错")


if __name__ == "__main__":
    test_all_encodings()
    test_garbage_raises()
    print("ok")
