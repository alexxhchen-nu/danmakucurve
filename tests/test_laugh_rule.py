"""笑类说法直接标开心，不进模型；别误伤普通弹幕。不需要 GPU。"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from llm_label import _fixed  # noqa: E402

LAUGH = ["起手就没绷住", "难绷", "抑郁症听了也憋不住", "半夜刷到 笑不行了", "给我笑的喘不上气了哥",
         "气笑了", "笑死", "这是什么玩意，给我笑炸了", "2333333", "猜到了，hhh", "哈哈哈"]
NOT = ["不浪费", "一滴都不浪费", "哈基米", "听哈气了", "就没偷摸骂我两句吧", "听了十遍还在听", "微笑"]


def test_laugh_goes_to_happy():
    out = _fixed(LAUGH + NOT)
    for t in LAUGH:
        assert out.get(t) == "开心", t
    for t in NOT:
        assert t not in out, t


if __name__ == "__main__":
    test_laugh_goes_to_happy()
    print("ok")
