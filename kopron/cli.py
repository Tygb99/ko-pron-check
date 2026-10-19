from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .compare import LEVELS, REASONS, compare, prep
from .g2p import RULE_NAMES, g2p

EXIT = {"pass": 0, "info": 0, "warn": 0, "fail": 1}


def _text(value: str | None, path: str | None) -> str:
    if path:
        return Path(path).read_text(encoding="utf-8")
    if value is None:
        sys.exit("give the text or a --*-file path")
    return value


def _format(result: dict[str, Any], lang: int) -> str:
    lines = [f"verdict: {result['verdict']}  " + " ".join(f"{k}={v}" for k, v in result["counts"].items())]
    for it in result["items"]:
        reasons = "; ".join(REASONS[r][lang] for r in it["reasons"])
        rules = ", ".join(RULE_NAMES[r][lang] for r in it["rules"])
        pron = f" [{it['ref_pron']}]/[{it['hyp_pron']}]" if it["ref_pron"] != it["ref"] or it["hyp_pron"] != it["hyp"] else ""
        lines.append(f"  {it['level'].upper():5} {it['ref'] or '-'} -> {it['hyp'] or '-'}{pron}  {reasons}"
                     + (f" ({rules})" if rules else ""))
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="kopron", description="Korean TTS script vs. transcript check by pronunciation")
    p.add_argument("--lang", choices=["ko", "en"], default="ko")
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("compare", help="compare one script with one transcript")
    c.add_argument("ref", nargs="?")
    c.add_argument("hyp", nargs="?")
    c.add_argument("--ref-file")
    c.add_argument("--hyp-file")
    c.add_argument("--json", action="store_true")
    c.add_argument("--strict", action="store_true", help="exit 2 on warnings")

    b = sub.add_parser("batch", help="compare REF_DIR/*.txt with HYP_DIR/<same name>")
    b.add_argument("ref_dir")
    b.add_argument("hyp_dir")
    b.add_argument("--json-out")
    b.add_argument("--strict", action="store_true")

    g = sub.add_parser("g2p", help="show the standard pronunciation")
    g.add_argument("text")

    r = sub.add_parser("prep", help="rewrite number dots as 쩜 before TTS")
    r.add_argument("file", nargs="?", help="default: stdin")
    r.add_argument("--keep-digits", action="store_true", help="2.5 -> 2쩜5 instead of 이 쩜 오")

    a = p.parse_args(argv)
    lang = 0 if a.lang == "ko" else 1

    if a.cmd == "g2p":
        print(g2p(a.text))
        return 0
    if a.cmd == "prep":
        src = Path(a.file).read_text(encoding="utf-8") if a.file else sys.stdin.read()
        out, skipped = prep(src, keep_digits=a.keep_digits)
        sys.stdout.write(out)
        for s in skipped:
            print(f"kopron: left as is (looks like a date): {s}", file=sys.stderr)
        return 0
    if a.cmd == "compare":
        result = compare(_text(a.ref, a.ref_file), _text(a.hyp, a.hyp_file))
        print(json.dumps(result, ensure_ascii=False, indent=1) if a.json else _format(result, lang))
        if a.strict and result["verdict"] == "warn":
            return 2
        return EXIT[result["verdict"]]

    worst, report = "pass", []
    for ref in sorted(Path(a.ref_dir).glob("*.txt")):
        hyp = Path(a.hyp_dir) / ref.name
        if not hyp.exists():
            print(f"{ref.name}: no transcript", file=sys.stderr)
            continue
        result = compare(ref.read_text(encoding="utf-8"), hyp.read_text(encoding="utf-8"))
        report.append({"name": ref.name, **result})
        print(f"== {ref.name}\n{_format(result, lang)}")
        if LEVELS.index(result["verdict"]) > LEVELS.index(worst):
            worst = result["verdict"]
    if a.json_out:
        Path(a.json_out).write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    if worst == "fail":
        return 1
    return 2 if (a.strict and worst == "warn") else 0


if __name__ == "__main__":
    raise SystemExit(main())
