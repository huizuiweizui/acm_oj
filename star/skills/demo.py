"""
演示：用一个虚构学生“小明”跑几句对话，打印每个 skill 的处理过程。

  python -m star.skills.demo            # 不调用大模型，意图识别使用关键词规则
  python -m star.skills.demo --llm      # 读取环境变量 LLM_API_KEY / LLM_API_URL / LLM_MODEL 调用大模型
  python -m star.skills.demo --pinyin   # 打开同音匹配（需安装 pypinyin）
"""
from __future__ import annotations

import argparse

from . import InputPipeline, LearnerView, OpenAICompatClient, SkillContext, Turn, check_reply

DEMO_PROFILE = {
    "name": "小明",
    "level": "starter",
    "glossary": {"呜呜车": "小火车", "嘀嘀": "提示", "飞走": "跳过"},
    "pronoun_reversal": True,
    "echolalia": True,
    "interests": ["火车"],
}

DIALOGS = [
    ("排好了吗？你也可以点提示。", [], "你要提示，呜呜车不走了"),
    ("排好了吗？你也可以点提示。", [], "你也可以点提示"),
    ("要不要看提示？", ["要", "不要"], "要"),
    ("你要不要看提示？", [], "不要看提示"),
    ("排好了吗？", [], "乌乌车卡住了"),
    ("排好了吗？", [], "啵啵仔不走了，我不会"),
]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--llm", action="store_true", help="调用真实大模型")
    ap.add_argument("--pinyin", action="store_true", help="打开同音匹配")
    args = ap.parse_args()

    llm = OpenAICompatClient.from_env() if args.llm else None
    pipe = InputPipeline(llm, use_pinyin=args.pinyin)
    learner = LearnerView.from_dict(DEMO_PROFILE)

    for system_text, options, student in DIALOGS:
        ctx = SkillContext(learner=learner, history=[Turn("system", system_text, options)],
                           step_prompt="把三张卡片排成正确顺序，让小火车到达终点")
        r = pipe.run(student, ctx)
        print("=" * 60)
        print(f"系统：{system_text}" + (f"  选项：{' / '.join(options)}" if options else ""))
        print(f"学生：{student}")
        for step in r.trace:
            d = step.data
            if step.skill == "segment":
                print(f"  [分词]     {' / '.join(t['word'] for t in d['tokens'])}")
            elif step.skill == "echo_detect":
                flag = "是仿说" if d["is_echo"] else "不是仿说"
                extra = f"，选了选项“{d['chosen_option']}”" if d["chosen_option"] else ""
                extra += f"，在回答正反问句（{'是' if d['yes_no'] else '否'}）" if d["yes_no"] is not None else ""
                print(f"  [仿说检测] {flag}（相似度 {d['score']}）{extra}")
            elif step.skill == "lexicon_map":
                maps = "；".join(f"{m['from']}→{m['to']}（{m['method']}）" for m in d["mappings"]) or "无"
                print(f"  [词表映射] {maps}；处理后：{d['text']}"
                      + (f"；候选新词：{'、'.join(d['candidate_words'])}" if d["candidate_words"] else ""))
            elif step.skill == "pronoun_tag":
                print(f"  [代词标注] {'；'.join(d['hints']) or '无提示'}")
            elif step.skill == "intent":
                print(f"  [意图识别] {d['intent']}（来源 {d['source']}）{d.get('restated', '')}")
            for n in step.notes:
                print(f"             备注：{n}")
        print(f"  => 最终意图：{r.intent['intent']}")

    print("=" * 60)
    reply = "小火车好像一条长龙，难道你不得不用循环吗？"
    res = check_reply(reply, SkillContext(learner=learner))
    print(f"[字面化检查] {reply}")
    for v in res["violations"]:
        print(f"  {v['severity']:7} {v['detail']}")
    print(f"  通过：{res['ok']}，统计：{res['stats']}")


if __name__ == "__main__":
    main()
