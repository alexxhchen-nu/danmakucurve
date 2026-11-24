"""DanmakuCurve：一个 B 站视频的弹幕 -> 情绪曲线 PNG。

用法：
  python run.py --url https://www.bilibili.com/video/BV1614y197xJ
  python run.py --xml data/sample_BV1614y197xJ.xml
可选：--bin 10（每段秒数） --out output/curve.png --csv output/labels.csv
"""
import argparse
import csv
import os
from collections import Counter

from danmaku import fetch_xml, parse_xml
from label import LABELS, label_all
from curve import plot

HERE = os.path.dirname(os.path.abspath(__file__))


def main(argv=None):
    ap = argparse.ArgumentParser()
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--url", help="B 站视频链接或 BV 号")
    src.add_argument("--xml", help="已保存的弹幕 XML 文件")
    ap.add_argument("--bin", type=int, default=10)
    ap.add_argument("--out", default=os.path.join(HERE, "output", "curve.png"))
    ap.add_argument("--csv", default=os.path.join(HERE, "output", "labels.csv"))
    ap.add_argument("--title", default="")
    a = ap.parse_args(argv)

    if a.url:
        try:
            title, xml_text = fetch_xml(a.url)
        except Exception as e:  # 网络被挡、B 站报错等
            raise SystemExit(f"抓不到弹幕（{type(e).__name__}: {e}）。"
                             f"可以先把弹幕 XML 存下来，再用 --xml 文件 来跑。")
    else:
        title = os.path.basename(a.xml)
        with open(a.xml, encoding="utf-8") as f:
            xml_text = f.read()

    rows = parse_xml(xml_text)
    labeled = label_all(rows)
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.csv, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["秒", "弹幕", "情绪"])
        w.writerows((f"{t:.1f}", txt, lab) for t, txt, lab in labeled)
    plot(labeled, a.out, title=a.title or title, bin_sec=a.bin)

    c = Counter(lab for _, _, lab in labeled)
    print(f"{len(labeled)} 条弹幕 | " + " ".join(f"{l} {c[l]}" for l in LABELS))
    print(f"图: {a.out}\n表: {a.csv}")
    return labeled


if __name__ == "__main__":
    main()
