"""给每条弹幕标 5 类情绪：开心、惊讶、感动、愤怒、无感。

免费、不用注册、不用 key：
  第 1 层：弹幕黑话词表（下面的 RULES，自己写的，随时可改）
  第 2 层：开源中文情绪词典 cnsenti（大连理工 DUTIR 情感词汇本体，7 类）
  都没命中 -> 无感

以后想换成 LLM，只要写一个同样签名的 label(text) -> str 函数替换即可。
"""
import re

LABELS = ["开心", "惊讶", "感动", "愤怒", "无感"]

# 同分时谁优先：越少见、越有信息量的排前面
PRIORITY = ["感动", "愤怒", "惊讶", "开心"]

# 每类：正则列表。命中一个记 1 分。
# 第二轮（全片 1200 条）加了：玩梗/角色扮演、比例错乱（"猫怎么这么大"）、夸人、emoji。
RULES = {
    "开心": [
        r"哈{2,}", r"h{3,}", r"2333*", r"笑死", r"笑[哭疯了]", r"好笑", r"乐死", r"乐了", r"^草+$",
        r"xswl", r"绷不住", r"没绷住", r"难绷", r"笑(得|的|到)?[^，。]{0,6}(喘|不行|炸|抽|死|疯|麻|裂|喷)", r"气笑", r"憋不住|憋下去", r"神人", r"蚌埠住", r"救命", r"嘿嘿", r"嘻嘻", r"啦啦啦",
        r"可爱", r"好乖", r"喜欢", r"爱了", r"爱上", r"好玩", r"有意思", r"有趣", r"开心", r"快乐",
        r"幸福", r"羡慕", r"好棒", r"太棒", r"不错", r"好看", r"甜", r"嗑", r"doge", r"狗头", r"滑稽",
        r"好耶", r"舒服", r"治愈", r"酷", r"想去", r"想住|也想住|能住", r"也能进", r"宠老婆",
        r"想当你的儿子|还缺儿子", r"好家伙",
        # 玩梗：书名号标题、"进击的…"、"道理我都懂"、给猫/孩子配台词、自嘲括号
        r"^《[^》]+》$", r"进击的", r"道理我都懂", r"既视感", r"私闯民宅", r"怪兽", r"巨兽", r"入侵",
        r"人类幼崽", r"^(?!原曲|原唱|bgm|BGM|出处|来源|省流|前面的|弹幕)[\u4e00-\u9fff]{1,3}\s*[:：∶]", r"[（(](bushi|确信|恳求|狗头|滑稽|doge)",
        r"[😂🤣😆😄😁😊🥰😍❤💕👍]",
    ],
    "惊讶": [
        r"卧槽", r"我去(?=[，,！!。？?\s]|$)", r"我靠", r"握草", r"我[勒嘞]个去", r"我[滴的]天", r"天[哪啊呐]", r"我的妈",
        r"居然", r"竟然", r"真[的能]?能", r"没想到", r"原来", r"震惊", r"离谱", r"不会吧",
        r"啊这", r"^啊[？?]", r"^[？?]+$", r"吓死|吓我",
        # 夸人（5 类里没有"佩服"，算惊讶）
        r"牛", r"\bnb\b", r"厉害|力害", r"太强|超强", r"强强", r"太顶", r"神了", r"天才|人才",
        r"创意", r"精致", r"手搓", r"666+", r"^\D{0,3}6+[!！]?$", r"边形", r"全能", r"天花板", r"豪华", r"细节",
        # 比例错乱：房子太小，看起来像巨猫
        r"这么大|太大了|巨型|巨猫", r"比例", r"分不清|搞不清|没概念", r"参照系", r"晕", r"恍惚",
        r"以为", r"第一反应", r"起猛了",
        r"有水|通水|通电|能用|能动",
        r"[？?]{2,}", r"[！!]{3,}", r"[？?][！!]|[！!][？?]",
        r"[😱😮😲🤯😳]",
    ],
    "感动": [
        r"泪目", r"哭了", r"想哭", r"感动", r"破防", r"呜+", r"眼泪", r"鼻子[一好]?酸",
        r"暖心", r"温暖", r"致敬", r"心疼", r"爷青回", r"怀念", r"回忆", r"加油",
        r"谢谢", r"感谢", r"最幸福", r"梦开始的地方|梦开始地方", r"泪",
        r"╥﹏╥|T_T|QAQ", r"[😭🥺]",
        # 第四轮：善意/功德类（"都是好心人""功德无量""你真好"）
        r"好心人|好人|功德|善良|你真好|善举",
    ],
    "愤怒": [
        r"气死", r"生气", r"恶心", r"^滚", r"垃圾", r"傻[逼b]", r"\bsb\b", r"什么玩意",
        r"无语", r"烦死", r"讨厌", r"有病", r"吐了", r"恶臭", r"差评", r"退钱", r"举报",
        r"气人", r"服了", r"[😡🤬💢]",
        # 第四轮：嫌弃/数落（"这鹿没素质""浪费水！可耻！"）；"不浪费""别浪费"不算
        r"没素质|素质[真太好]?[低差]|缺德|可耻|这么坏|真坏|太坏|坏[比b]",
        r"(?<![不别没免])浪费",
    ],
}
# 刷屏广告直接算无感（这个视频里有一批"炒股小说"广告弹幕）
# 广告和模板刷屏（正在看、弹幕飞过等）一律判无感
SPAM = re.compile(r"藩茄|富豪股神|全款购|^(正在看|正在刷弹幕|弹幕飞过|学到了|打卡|前排)$")
# 笑类说法：小模型（1.5B）认不稳，这些直接标开心，不交给模型。
LAUGH = re.compile(r"没绷住|绷不住|难绷|憋(?:不住|笑|下去)|气笑|笑死|笑不行|笑[得的]?喘|笑炸|笑疯|哈{2,}|2333|hhh", re.I)
_COMPILED = {k: [re.compile(p, re.I) for p in v] for k, v in RULES.items()}

# cnsenti 的 7 类 -> 我们的 5 类。
# 只用 乐/怒/惧：在样例弹幕上试过，"好"把"确实"标成开心，"恶"/"哀"/"惊"也大多标错，所以不用。
DUTIR_MAP = {"乐": "开心", "怒": "愤怒", "惧": "惊讶"}

_emotion = None


def _dutir(text):
    """cnsenti 词典打分；没装就跳过。"""
    global _emotion
    if _emotion is False:
        return None
    if _emotion is None:
        try:
            import logging
            import jieba
            jieba.setLogLevel(logging.WARNING)
            from cnsenti import Emotion
            _emotion = Emotion()
        except Exception:
            _emotion = False
            return None
    counts = _emotion.emotion_count(text)
    scores = {}
    for k, ours in DUTIR_MAP.items():
        scores[ours] = scores.get(ours, 0) + counts.get(k, 0)
    return _pick(scores)


def _pick(scores):
    best = max(scores.values(), default=0)
    if best <= 0:
        return None
    for lab in PRIORITY:
        if scores.get(lab, 0) == best:
            return lab
    return None


def label(text):
    if SPAM.search(text):
        return "无感"
    scores = {lab: sum(1 for p in pats if p.search(text)) for lab, pats in _COMPILED.items()}
    # 带“笑”的句子（如“什么玩意，给我笑炸了”）是在笑，不算愤怒
    if "笑" in text and scores.get("开心"):
        scores["愤怒"] = 0
    # 带玩笑标记（bushi、doge、狗头）的不算感动，如“功德+3（bushi）”
    if re.search(r"bushi|doge|狗头", text, re.I):
        scores["感动"] = 0
    return _pick(scores) or _dutir(text) or "无感"


def label_all(rows):
    """[(t, text)] -> [(t, text, 情绪)]"""
    return [(t, txt, label(txt)) for t, txt in rows]
