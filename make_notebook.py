"""把本文件夹的代码打包成一个 Colab notebook：DanmakuCurve.ipynb。
改了 danmaku.py / label.py / curve.py / llm_label.py 之后，重新跑一次：python make_notebook.py
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
WORKDIR = "/content/danmakucurve"
MODULES = ["danmaku.py", "label.py", "curve.py", "llm_label.py"]


def md(text):
    return {"cell_type": "markdown", "metadata": {}, "source": text.strip("\n").splitlines(True)}


def code(text, form=True):
    meta = {"cellView": "form"} if form else {}
    return {"cell_type": "code", "metadata": meta, "execution_count": None, "outputs": [],
            "source": text.strip("\n").splitlines(True)}


INTRO = """
# DanmakuCurve：B 站弹幕情绪曲线

贴一个 B 站视频链接，把弹幕标成 **开心 / 惊讶 / 感动 / 愤怒 / 无感**，按视频时间画成曲线。

**怎么用（3 步）**
1. 菜单 **代码执行程序 → 更改运行时类型**，选 **T4 GPU**，保存（只要设一次）。
2. 在下面 ① 里换成你的视频链接。
3. 菜单 **代码执行程序 → 全部运行**。第一次会问"仍然运行"，点它。

图会显示在最下面，PNG 和 CSV 会自动下载。

免费：用的是开源小模型 Qwen2.5-1.5B-Instruct（Apache 2.0），不用 key，不用注册。没有 GPU 时自动改用弹幕词表。
请只用来分析不涉及政治的视频。
"""

SETTINGS = """
#@title ① 填链接
视频链接 = "https://www.bilibili.com/video/BV1JjZsYHEHE"  #@param {type:"string"}
每段秒数 = 5  #@param {type:"integer"}
标注方式 = "小模型（免费，需 GPU）"  #@param ["小模型（免费，需 GPU）", "词表（最快）", "API（需要 key）"]
模型 = "Qwen/Qwen2.5-1.5B-Instruct"  #@param ["Qwen/Qwen2.5-1.5B-Instruct", "Qwen/Qwen2.5-0.5B-Instruct"]
"""

API = """
#@title （可选）API 设置：只有 ① 里选了「API」才会用
# key 不要写在这里。点左边栏的钥匙图标（密钥 / Secrets），新建一个叫 LLM_API_KEY 的密钥，把 key 填进去，并打开"笔记本访问权限"。
API地址 = "https://api.together.xyz/v1"  #@param ["https://api.together.xyz/v1", "https://api.z.ai/api/paas/v4"]
API模型 = "Qwen/Qwen2.5-7B-Instruct-Turbo"  #@param {type:"string"}
"""

RUN = """
#@title ③ 跑起来
import collections
import os
import sys

sys.path.insert(0, WORKDIR)
from IPython.display import Image, display

from curve import plot
from danmaku import bvid_from_url, fetch_xml, parse_xml
from label import LABELS, label_all

try:
    bv = bvid_from_url(视频链接)
except ValueError:
    bv = "video"

# 1. 抓弹幕；抓不到就让你上传 XML
try:
    标题, xml_text = fetch_xml(视频链接)
    print("抓到了：", 标题)
except Exception as e:
    print(f"直接抓不到弹幕（{type(e).__name__}: {e}）")
    print("可以手动存一份弹幕 XML 再上传：")
    print(f"  1) 浏览器打开 https://api.bilibili.com/x/player/pagelist?bvid={bv} ，找到 cid 后面的数字")
    print("  2) 打开 https://api.bilibili.com/x/v1/dm/list.so?oid=那个数字 ，另存为 .xml")
    print("  3) 点下面的「选择文件」上传")
    from google.colab import files
    up = files.upload()
    name = next(iter(up))
    xml_text, 标题 = up[name].decode("utf-8"), os.path.splitext(name)[0]

rows = parse_xml(xml_text)
print(len(rows), "条弹幕")

# 2. 标情绪
用了 = "词表"
if 标注方式.startswith("小模型"):
    import torch
    if torch.cuda.is_available():
        try:
            from llm_label import LLMLabeler, label_all_llm
            print("下载并加载模型（第一次约 1–2 分钟）……")
            labeler = LLMLabeler(模型)
            labeled = label_all_llm(rows, labeler, progress=lambda a, b: print(f"\\r标注 {a}/{b}", end=""))
            print()
            用了 = 模型.split("/")[-1] + "+笑类词表"
        except Exception as e:
            print(f"\\n小模型出错（{type(e).__name__}: {e}），改用词表。")
            labeled = label_all(rows)
    else:
        print("现在没有 GPU，先用词表。想用小模型：代码执行程序 → 更改运行时类型 → T4 GPU，再全部运行。")
        labeled = label_all(rows)
elif 标注方式.startswith("API"):
    from google.colab import userdata
    from llm_label import label_all_api
    try:
        key = userdata.get("LLM_API_KEY")
    except Exception:
        raise SystemExit("没找到密钥 LLM_API_KEY。左边栏钥匙图标里新建它，并打开笔记本访问权限。")
    labeled = label_all_api(rows, key, API地址, API模型)
    用了 = API模型
else:
    labeled = label_all(rows)

# 3. 对比词表、画图、存文件
词表 = collections.Counter(l for _, _, l in label_all(rows))
这次 = collections.Counter(l for _, _, l in labeled)
print(f"各情绪条数（{用了} / 词表）：")
for lab in LABELS:
    print(f"  {lab}: {这次[lab]} / {词表[lab]}")

png, csv_path = f"curve_{bv}.png", f"labels_{bv}.csv"
import csv
with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["秒", "弹幕", "情绪"])
    w.writerows((f"{t:.1f}", txt, lab) for t, txt, lab in labeled)
plot(labeled, png, title=f"《{标题}》{len(rows)} 条弹幕（{用了}）", bin_sec=每段秒数)
display(Image(png))
try:
    from google.colab import files
    files.download(png)
    files.download(csv_path)
except Exception:
    print("已保存：", png, csv_path)
"""


def setup_cell():
    lines = [
        "#@title ② 准备环境（不用改，约 1 分钟）",
        "!pip -q install jieba cnsenti",
        "!apt-get -qq install -y fonts-noto-cjk > /dev/null",
        "import os",
        f'WORKDIR = "{WORKDIR}"',
        "os.makedirs(WORKDIR, exist_ok=True)",
        "",
    ]
    for name in MODULES:
        src = open(os.path.join(HERE, name), encoding="utf-8").read()
        assert "'''" not in src, name
        lines.append(f"open(os.path.join(WORKDIR, {name!r}), 'w', encoding='utf-8').write(r'''{src}''')")
    lines.append('print("准备好了")')
    return code("\n".join(lines))


def build(path=os.path.join(HERE, "DanmakuCurve.ipynb")):
    nb = {
        "nbformat": 4, "nbformat_minor": 0,
        "metadata": {
            "colab": {"provenance": [], "gpuType": "T4"},
            "accelerator": "GPU",
            "kernelspec": {"name": "python3", "display_name": "Python 3"},
            "language_info": {"name": "python"},
        },
        "cells": [md(INTRO), code(SETTINGS), setup_cell(), code(API), code(RUN)],
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(nb, f, ensure_ascii=False, indent=1)
    return path


if __name__ == "__main__":
    print(build())
