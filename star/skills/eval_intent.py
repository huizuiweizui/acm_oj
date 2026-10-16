"""
意图理解消融实验（测试方案第三组）。

对每条测试语句分别用两种配置跑一遍，按类别统计准确率：
  - full    ：开启全部 skill
  - no_comm ：关闭沟通特征处理（仿说检测、词表映射、代词标注）

  python -m star.skills.eval_intent                                   # 用自带样例，关键词规则模式
  python -m star.skills.eval_intent path/to/samples.jsonl --llm       # 调用大模型
  python -m star.skills.eval_intent --llm --out result.json           # 同时保存逐条结果

测试集格式（每行一个 JSON）：
  {"id": "echo-01", "category": "echo", "profile": {...}, "step": "...",
   "history": [{"role": "system", "text": "...", "options": []}],
   "input": "学生原话", "expected": "echo"}
expected 取值：intents 中的意图，或 "echo"（应判定为仿说）。
自带样例只用来演示格式，正式测试的 50 条语句需要人工逐条核对标注。
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

from . import COMM_SKILLS, InputPipeline, LearnerView, OpenAICompatClient, SkillContext, Turn

DEFAULT_SAMPLES = Path(__file__).resolve().parent / "data" / "intent_samples.jsonl"
CATEGORY_NAMES = {"echo": "仿说", "pronoun": "代词逆转", "neologism": "自创词", "plain": "普通表达"}


def load(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def evaluate(samples: list[dict], pipe: InputPipeline) -> list[dict]:
    rows = []
    for s in samples:
        ctx = SkillContext(learner=LearnerView.from_dict(s.get("profile")),
                           history=[Turn.from_dict(t) for t in s.get("history", [])],
                           step_prompt=s.get("step", ""))
        r = pipe.run(s["input"], ctx)
        rows.append({"id": s["id"], "category": s.get("category", "plain"), "input": s["input"],
                     "expected": s["expected"], "predicted": r.intent["intent"],
                     "source": r.intent.get("source"), "correct": r.intent["intent"] == s["expected"]})
    return rows


def summarize(rows: list[dict]) -> dict[str, tuple[int, int]]:
    acc: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for r in rows:
        for key in (r["category"], "all"):
            acc[key][0] += int(r["correct"])
            acc[key][1] += 1
    return {k: (v[0], v[1]) for k, v in acc.items()}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("samples", nargs="?", default=str(DEFAULT_SAMPLES))
    ap.add_argument("--llm", action="store_true", help="调用真实大模型")
    ap.add_argument("--pinyin", action="store_true", help="打开同音匹配")
    ap.add_argument("--out", help="把逐条结果保存为 JSON")
    args = ap.parse_args()

    samples = load(Path(args.samples))
    llm = OpenAICompatClient.from_env() if args.llm else None
    configs = {
        "full": InputPipeline(llm, use_pinyin=args.pinyin),
        "no_comm": InputPipeline(llm, use_pinyin=args.pinyin, disabled=COMM_SKILLS),
    }
    results = {name: evaluate(samples, pipe) for name, pipe in configs.items()}
    summaries = {name: summarize(rows) for name, rows in results.items()}

    cats = [c for c in CATEGORY_NAMES if c in summaries["full"]] + ["all"]
    print(f"模式：{'大模型' if llm else '关键词规则'}，样本数：{len(samples)}")
    print(f"{'类别':<10}{'关闭沟通特征处理':>14}{'开启全部 skill':>14}")
    for c in cats:
        name = CATEGORY_NAMES.get(c, "合计")
        cells = []
        for cfg in ("no_comm", "full"):
            ok, n = summaries[cfg][c]
            cells.append(f"{ok}/{n} ({ok / n:.0%})")
        print(f"{name:<10}{cells[0]:>16}{cells[1]:>16}")

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"逐条结果已保存到 {args.out}")


if __name__ == "__main__":
    main()
