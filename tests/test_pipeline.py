"""离线测试：不用联网。运行：python -m unittest discover -s tests"""
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from danmaku import bvid_from_url, parse_xml  # noqa: E402
from label import LABELS, label  # noqa: E402
from curve import bin_counts  # noqa: E402
import run  # noqa: E402

SAMPLE = os.path.join(ROOT, "data", "sample_BV1614y197xJ.xml")


class TestPipeline(unittest.TestCase):
    def test_bvid(self):
        self.assertEqual(bvid_from_url("https://www.bilibili.com/video/BV1614y197xJ/?p=1"), "BV1614y197xJ")
        with self.assertRaises(ValueError):
            bvid_from_url("https://example.com")

    def test_parse_sample(self):
        rows = parse_xml(open(SAMPLE, encoding="utf-8").read())
        self.assertEqual(len(rows), 1200)  # 全片（接口上限）
        self.assertEqual([t for t, _ in rows], sorted(t for t, _ in rows))  # 按时间排好
        self.assertEqual(rows[0], (0.0, "入站必刷"))

    def test_labels(self):
        cases = {
            "噗哈哈哈哈哈哈哈这名字可以": "开心",
            "这个电梯居然能动": "惊讶",
            "还有电视看！卧槽！": "惊讶",
            "泪目了": "感动",
            "太恶心了，退钱": "愤怒",
            "@设计师王姨": "无感",
            "确实": "无感",
            # 第二轮：玩梗、比例错乱、夸人、emoji、广告
            "《进击的巨人》": "开心",
            "猫∶救命我家里来了怪兽": "开心",
            "我的大脑和我的比例尺在打架": "惊讶",
            "牛啊": "惊讶",
            "太好笑了😂": "开心",
            "这也太离谱了吧😱": "惊讶",
            "看哭了😭": "感动",
            "我能拥有深圳的全款房产，全得益于《富豪股神绝招》": "无感",
            "第一句就没绷住": "开心",
            "这是什么玩意，给我笑炸了": "开心",
            "正在看": "无感",
            "原曲：non je ne regrette rien": "无感",
            # 第四轮：暖心话、玩笑标记、数落、"省流："、"我去"当动词
            "都是好心人": "感动",
            "功德+3（bushi）": "开心",
            "浪费水！可耻！": "愤怒",
            "一滴都不浪费": "无感",
            "省流：漏水了": "无感",
            "这是哪个山 我去遛达遛达": "无感",
        }
        for text, want in cases.items():
            self.assertEqual(label(text), want, text)

    def test_bins(self):
        labeled = [(1, "a", "开心"), (9.9, "b", "惊讶"), (10, "c", "开心"), (25, "d", "无感")]
        starts, counts = bin_counts(labeled, bin_sec=10)
        self.assertEqual(starts, [0, 10, 20])
        self.assertEqual(counts["开心"], [1, 1, 0])
        self.assertEqual(sum(sum(v) for v in counts.values()), 4)

    def test_end_to_end(self):
        with tempfile.TemporaryDirectory() as d:
            png, csv_path = os.path.join(d, "c.png"), os.path.join(d, "l.csv")
            labeled = run.main(["--xml", SAMPLE, "--out", png, "--csv", csv_path])
            self.assertEqual(len(labeled), 1200)
            self.assertTrue(all(lab in LABELS for _, _, lab in labeled))
            with open(png, "rb") as f:
                self.assertEqual(f.read(8), b"\x89PNG\r\n\x1a\n")


if __name__ == "__main__":
    unittest.main()
