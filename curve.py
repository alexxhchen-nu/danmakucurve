"""按视频时间分段，统计每段各情绪条数，画成 PNG。"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

from label import LABELS

# 紫色为主色（开心），其余三色用来区分；已检查色盲可分辨
COLORS = {"开心": "#7c3aed", "惊讶": "#0891b2", "感动": "#db2777",
          "愤怒": "#d97706", "无感": "#a1a1aa"}
BAR = "#ede9fe"  # 每段弹幕总数的底色（浅紫）

_CJK = ["WenQuanYi Zen Hei", "Noto Sans CJK SC", "Noto Sans CJK JP", "Noto Sans SC", "PingFang SC",
        "Microsoft YaHei", "SimHei", "Heiti SC", "Source Han Sans SC"]


def _set_cjk_font():
    # Colab 装完 fonts-noto-cjk 后，matplotlib 还不认识，手动登记一下
    import glob
    for path in glob.glob("/usr/share/fonts/**/*CJK*", recursive=True):
        try:
            font_manager.fontManager.addfont(path)
        except Exception:
            pass
    have = {f.name for f in font_manager.fontManager.ttflist}
    for name in _CJK:
        if name in have:
            # 英文和数字用 DejaVu Sans（matplotlib 自带），中文字符自动回退到中文字体
            plt.rcParams["font.family"] = ["DejaVu Sans", name]
            plt.rcParams["axes.unicode_minus"] = False
            return True
    return False


def bin_counts(labeled, bin_sec=10, duration=None):
    """-> (起点秒数列表, {情绪: [每段条数]})"""
    end = duration if duration else (max(t for t, _, _ in labeled) if labeled else 0)
    n = int(end // bin_sec) + 1
    counts = {lab: [0] * n for lab in LABELS}
    for t, _, lab in labeled:
        i = min(int(t // bin_sec), n - 1)
        counts[lab][i] += 1
    return [i * bin_sec for i in range(n)], counts


def plot(labeled, out_png, title="", bin_sec=10, show_neutral=False):
    starts, counts = bin_counts(labeled, bin_sec)
    _set_cjk_font()
    fig, ax = plt.subplots(figsize=(11, 4.5), dpi=150)
    labs = [l for l in LABELS if show_neutral or l != "无感"]
    for lab in labs:
        ax.plot(starts, counts[lab], marker="o", ms=3, lw=2, color=COLORS[lab], label=lab)
    total = [sum(counts[l][i] for l in LABELS) for i in range(len(starts))]
    ax.bar(starts, total, width=bin_sec * 0.9, align="edge", color=BAR,
           label="全部弹幕", zorder=0)
    ax.set_xlabel(f"视频时间（秒，每 {bin_sec} 秒一段）")
    ax.set_ylabel("弹幕条数")
    ax.set_title(title or "弹幕情绪曲线")
    ax.legend(ncol=6, loc="upper right", frameon=False, fontsize=9)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(out_png)
    plt.close(fig)
    return out_png
