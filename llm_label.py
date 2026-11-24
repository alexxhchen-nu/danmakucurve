"""用免费开源小模型（默认 Qwen2.5-1.5B-Instruct，Apache 2.0）给弹幕标 5 类情绪。

不用 key、不用注册。需要 GPU（Colab 免费 T4 就够）。
做法：让模型读一条弹幕，只比较 5 个标签第一个字的概率，挑最大的，
所以输出一定是 5 类之一，不会胡写。
广告和模板刷屏先判成无感；没绷住、难绷、笑死这类笑的说法先判成开心（词表优先），都不进模型。
"""
from label import LABELS, LAUGH, SPAM

DEFAULT_MODEL = "Qwen/Qwen2.5-1.5B-Instruct"

SYSTEM = (
    "你是 B 站弹幕情绪标注员。每次给你一条弹幕，只回答一个词：开心、惊讶、感动、愤怒、无感。\n"
    "开心：好笑、玩梗、可爱、喜欢、调侃。\n"
    "惊讶：意外、震惊、佩服、没想到。\n"
    "感动：泪目、暖心、感谢、致敬、心疼。\n"
    "愤怒：生气、嫌弃、骂人、数落。\n"
    "无感：只是陈述、提问、刷屏，看不出情绪。\n"
    "注意 B 站说法：没绷住、绷不住、难绷、憋不住、憋笑、气笑了、笑死、笑喘不上气、2333、hhh 都是在笑，算开心，不是惊讶。\n"
    "例子：\n"
    "弹幕：没绷住，上来就溜达了 → 开心\n"
    "弹幕：气笑了 → 开心\n"
    "弹幕：给我笑的喘不上气了哥 → 开心\n"
    "弹幕：居然是他？？ → 惊讶\n"
    "弹幕：今天下雨了 → 无感"
)


def _fixed(texts):
    """不用问模型的弹幕：刷屏 -> 无感，笑类说法 -> 开心。"""
    out = {}
    for t in texts:
        if SPAM.search(t):
            out[t] = "无感"
        elif LAUGH.search(t):
            out[t] = "开心"
    return out


class LLMLabeler:
    def __init__(self, model_name=DEFAULT_MODEL, device=None):
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        self.torch = torch
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.tok = AutoTokenizer.from_pretrained(model_name)
        self.tok.padding_side = "left"
        if self.tok.pad_token is None:
            self.tok.pad_token = self.tok.eos_token
        dtype = torch.float16 if self.device == "cuda" else torch.float32
        self.model = AutoModelForCausalLM.from_pretrained(model_name, torch_dtype=dtype).to(self.device).eval()
        # 每个标签的第一个 token；5 个必须互不相同
        self.first_ids = [self.tok.encode(lab, add_special_tokens=False)[0] for lab in LABELS]
        if len(set(self.first_ids)) != len(LABELS):
            raise RuntimeError("这个模型的分词把两个标签开头切成一样了，换个模型试试")

    def _prompt(self, text):
        msgs = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": f"弹幕：{text}"}]
        return self.tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)

    def label_texts(self, texts, batch_size=32, progress=None):
        """[文本] -> [情绪]。重复的弹幕只算一次。"""
        out = _fixed(texts)
        uniq = [t for t in dict.fromkeys(texts) if t not in out]
        ids = self.torch.tensor(self.first_ids, device=self.device)
        for i in range(0, len(uniq), batch_size):
            chunk = uniq[i:i + batch_size]
            enc = self.tok([self._prompt(t) for t in chunk], return_tensors="pt", padding=True).to(self.device)
            with self.torch.no_grad():
                logits = self.model(**enc).logits[:, -1, :]  # 左侧补齐，最后一位就是下一个字
            best = logits.index_select(1, ids).argmax(dim=1).tolist()
            for t, b in zip(chunk, best):
                out[t] = LABELS[b]
            if progress:
                progress(min(i + batch_size, len(uniq)), len(uniq))
        return [out.get(t, "无感") for t in texts]


def label_all_llm(rows, labeler, **kw):
    """[(t, text)] -> [(t, text, 情绪)]"""
    labs = labeler.label_texts([txt for _, txt in rows], **kw)
    return [(t, txt, lab) for (t, txt), lab in zip(rows, labs)]


def label_all_api(rows, api_key, base_url, model, batch_size=40):
    """可选：用 OpenAI 兼容接口（Together、Z.ai 等）标注。key 从 Colab Secrets 读，不写进代码。"""
    import re

    import requests

    texts = [txt for _, txt in rows]
    out = _fixed(texts)
    uniq = [t for t in dict.fromkeys(texts) if t not in out]
    for i in range(0, len(uniq), batch_size):
        chunk = uniq[i:i + batch_size]
        listing = "\n".join(f"{j + 1}. {t}" for j, t in enumerate(chunk))
        body = {
            "model": model,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": f"下面有 {len(chunk)} 条弹幕。按顺序每行只写一个情绪词，共 {len(chunk)} 行，不要编号。\n{listing}"},
            ],
        }
        r = requests.post(base_url.rstrip("/") + "/chat/completions", json=body, timeout=120,
                          headers={"Authorization": f"Bearer {api_key}"})
        r.raise_for_status()
        lines = r.json()["choices"][0]["message"]["content"].strip().splitlines()
        for t, line in zip(chunk, lines):
            m = re.search("|".join(LABELS), line)
            out[t] = m.group(0) if m else "无感"
    return [(t, txt, out.get(txt, "无感")) for t, txt in rows]
