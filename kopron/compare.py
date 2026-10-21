"""Compare a TTS script with a speech-recognition transcript by pronunciation."""
from __future__ import annotations

import itertools
import re
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any

from .g2p import LAX, WILD_UI, Syl, apply_rules, decompose, g2p
from .numbers import (DOMAIN_DOTS, DOT_OK, DOT_WRONG, LIMIT, SYMBOLS, TLDS, digitwise, latin_readings,
                      number_readings, sino)

TOKEN = re.compile(r"(?P<num>\d+(?:[.,]\d+)*)"
                   r"|(?P<lat>[A-Za-z](?:\.[A-Za-z](?![A-Za-z]))+\.?|[A-Za-z]+)"
                   rf"|(?P<dom>(?<=[A-Za-z0-9])\.(?=(?i:{'|'.join(TLDS)})(?![A-Za-z])))"
                   r"|(?P<sym>%)|(?P<han>[가-힣])|(?P<sp>.)", re.S)
LEVELS = ["pass", "info", "warn", "fail"]
MERGED_VOWELS = [{"ㅐ", "ㅔ"}, {"ㅒ", "ㅖ"}, {"ㅙ", "ㅚ", "ㅞ"}]
WEAK_H_AFTER = {"", "ㄴ", "ㄹ", "ㅁ", "ㅇ"}
JEOM_IN_DIGITS = re.compile(r"\d+\s*점\s*\d+")
DOMAIN_DOT_SYLS = {t for t, _ in DOMAIN_DOTS}
TLD_START = {"컴", "넷", "오", "케", "코", "씨"}

REASONS = {
    "pron": ("표준 발음이 같음", "same standard pronunciation"),
    "tensing": ("된소리되기(제24~28항, 제30항). 낱말 구조를 봐야 정해져 양쪽을 다 인정",
                "tensing (clauses 24-28, 30); depends on word structure, so both are accepted"),
    "number": ("숫자를 글자로 적었거나 글자를 숫자로 적은 차이", "digits written as words or words as digits"),
    "latin": ("영문자를 글자 이름으로 읽은 차이", "Latin letters read by their names"),
    "dot_jjeom": ("숫자 속 「.」을 「쩜」으로 읽음", "the dot inside a number was read 쩜"),
    "dot_jeom": ("숫자 속 「.」을 「점」으로 읽음. 「쩜」으로 읽어야 함",
                 "the dot inside a number was read 점; it should be 쩜"),
    "dot_domain": ("주소 속 「.」을 「닷」이나 「쩜」으로 읽음(둘 다 인정)",
                   "the dot in a web address read 닷 or 쩜; both are accepted"),
    "dot_unverified": ("받아쓰기가 숫자로 적어서 「.」을 점·쩜 중 무엇으로 읽었는지 알 수 없음",
                       "the transcript kept the digits, so 점 vs 쩜 cannot be told"),
    "ae_e": ("ㅐ/ㅔ(ㅒ/ㅖ, ㅙ/ㅚ/ㅞ) 차이. 표준 발음은 구별하지만 받아쓰기가 잘 못 가름. 귀로 확인",
             "ㅐ/ㅔ-type vowel difference; standard Korean keeps them apart but recognizers often cannot. Listen"),
    "h_weak": ("ㅎ이 약하게 들림(표준 발음은 아니지만 흔한 말소리). 귀로 확인",
               "weakened ㅎ (not standard, but common in speech). Listen"),
    "mismatch": ("발음이 다름", "different pronunciation"),
    "extra": ("받아쓰기에만 있음", "only in the transcript"),
    "missing": ("원고에만 있음", "only in the script"),
}


@dataclass
class Unit:
    kind: str
    text: str
    syl: Syl | None = None
    glued: bool = False  # digits written right after Latin letters, as in abc99

    def key(self):
        if self.syl is not None:
            return self.syl.key()
        return (self.kind, self.text.lower())


def tokenize(text: str, weaken_h: bool = False) -> list[Unit]:
    units: list[Unit] = []
    word_start = True
    prev_kind, prev_end = "", -1
    for m in TOKEN.finditer(unicodedata.normalize("NFC", text)):
        kind, tok = m.lastgroup or "sp", m.group()
        if kind == "han":
            units.append(Unit("H", tok, decompose(tok, word_start)))
            word_start = False
        elif kind == "sp":
            word_start = True
        else:
            glued = kind == "num" and prev_kind == "lat" and prev_end == m.start()
            units.append(Unit(kind.upper(), tok, glued=glued))
            word_start = True
        prev_kind, prev_end = kind, m.end()
    if weaken_h:
        for prev, cur in zip(units, units[1:]):
            if prev.syl and cur.syl and cur.syl.c == "ㅎ" and prev.syl.f in WEAK_H_AFTER:
                cur.syl.c = "ㅇ"
    run: list[Syl] = []
    for u in units + [Unit("END", "")]:
        if u.syl is not None:
            run.append(u.syl)
        else:
            apply_rules(run)
            run = []
    return units


def _worse(a: str, b: str) -> str:
    return a if LEVELS.index(a) >= LEVELS.index(b) else b


def _has_final_before(units: list[Unit], i: int) -> bool:
    prev = units[i - 1].syl if i > 0 else None
    return prev is not None and prev.f != ""


def _same_vowel(a: str, b: str) -> bool:
    if a == b:
        return True
    if WILD_UI in (a, b):
        return ({a, b} - {WILD_UI}) <= {"ㅢ", "ㅣ", "ㅔ"}
    return False


def _before_tld(units: list[Unit], i: int) -> bool:
    return i + 1 < len(units) and units[i + 1].kind == "H" and units[i + 1].text in TLD_START


def _positions(r: list[Unit], h: list[Unit], i: int, j: int, n: int):
    level, reasons, rules = "pass", set(), set()
    for k in range(n):
        a, b = r[i + k], h[j + k]
        sa, sb = a.syl, b.syl
        assert sa is not None and sb is not None
        if a.text == DOT_OK and b.text == DOT_WRONG:
            level = _worse(level, "warn"); reasons.add("dot_jeom"); continue
        if a.text == DOT_WRONG and b.text == DOT_OK:
            reasons.add("dot_jjeom"); continue
        if (a.text != b.text and {a.text, b.text} <= DOMAIN_DOT_SYLS
                and _before_tld(r, i + k) and _before_tld(h, j + k)):
            if b.text == DOT_WRONG:
                level = _worse(level, "warn"); reasons.add("dot_jeom")
            else:
                reasons.add("dot_domain")
            continue
        rules |= sa.rules | sb.rules
        c_ok = sa.c == sb.c
        if not c_ok and LAX.get(sa.c, sa.c) == LAX.get(sb.c, sb.c) and (
                _has_final_before(r, i + k) or _has_final_before(h, j + k)):
            c_ok = True; reasons.add("tensing")
        v_ok = _same_vowel(sa.v, sb.v)
        v_merged = not v_ok and any({sa.v, sb.v} <= s for s in MERGED_VOWELS)
        if not (c_ok and sa.f == sb.f and (v_ok or v_merged)):
            return "fail", {"mismatch"}, rules
        if v_merged:
            level = _worse(level, "warn"); reasons.add("ae_e")
        if a.key() != b.key() and not reasons:
            reasons.add("pron")
    return level, reasons or {"pron"}, rules


def _expand(units: list[Unit], heard: bool = False) -> list[tuple[str, bool]]:
    choices = []
    for u in units:
        if u.kind == "H" and u.text == DOT_WRONG:
            choices.append([(DOT_WRONG, False), (DOT_OK, heard)])
        elif u.kind == "H":
            choices.append([(u.text, False)])
        elif u.kind == "NUM":
            glued = u.glued and u.text.isdigit()
            choices.append(number_readings(u.text) + ([(x, False) for x in digitwise(u.text)] if glued else []))
        elif u.kind == "DOM":
            choices.append(DOMAIN_DOTS)
        elif u.kind == "LAT":
            choices.append([(x, False) for x in latin_readings(u.text)] + [(u.text.lower(), False)])
        else:
            choices.append([(x, False) for x in SYMBOLS.get(u.text, [u.text])])
    out = []
    for combo in itertools.islice(itertools.product(*choices), LIMIT):
        out.append(("".join(t for t, _ in combo), any(w for _, w in combo)))
    return out


def _readings_match(ref: list[Unit], hyp: list[Unit]):
    hyp_prons: dict[str, bool] = {}
    for text, wrong in _expand(hyp, heard=True):
        p = g2p(text)
        hyp_prons[p] = hyp_prons.get(p, True) and wrong
    found = None
    for text, wrong in _expand(ref):
        p = g2p(text)
        if p in hyp_prons:
            w = wrong or hyp_prons[p]
            if not w:
                return False
            found = True
    return found


def _span(units: list[Unit]) -> str:
    return " ".join(u.text for u in units) if any(u.kind != "H" for u in units) else "".join(u.text for u in units)


def _pron(units: list[Unit]) -> str:
    return "".join(u.syl.text() if u.syl else u.text for u in units)


def _item(level, ref, hyp, reasons, rules=()):
    return {"level": level, "ref": _span(ref), "hyp": _span(hyp),
            "ref_pron": _pron(ref), "hyp_pron": _pron(hyp),
            "reasons": sorted(reasons), "rules": sorted(set(rules), key=int)}


def _classify(r, h, ra, ha, i1, i2, j1, j2):
    R, H = r[i1:i2], h[j1:j2]
    if not R:
        return _item("fail", R, H, {"extra"})
    if not H:
        return _item("fail", R, H, {"missing"})
    if all(u.syl for u in R + H):
        if len(R) == len(H):
            level, reasons, rules = _positions(r, h, i1, j1, len(R))
            if level != "fail":
                return _item(level, R, H, reasons, rules)
            level, reasons, rules = _positions(ra, ha, i1, j1, len(R))
            if level != "fail":
                return _item("warn", R, H, (reasons - {"pron"}) | {"h_weak"}, rules)
        return _item("fail", R, H, {"mismatch"})
    wrong_dot = _readings_match(R, H)
    if wrong_dot is None:
        return _item("fail", R, H, {"mismatch"})
    kinds = {u.kind for u in R + H}
    reason = "number" if "NUM" in kinds or "SYM" in kinds else "latin"
    if wrong_dot:
        return _item("warn", R, H, {reason, "dot_jeom"})
    has_dot = any(u.kind == "NUM" and "." in u.text for u in R + H)
    return _item("pass", R, H, {reason, "dot_jjeom"} if has_dot else {reason})


def compare(ref: str, hyp: str) -> dict[str, Any]:
    """Compare script ``ref`` with transcript ``hyp``.

    Returns {"verdict": pass|info|warn|fail, "items": [...], "counts": {...}}.
    Differences that are only standard sound changes come back as level "pass"
    with the clause numbers that explain them.
    """
    r, h = tokenize(ref), tokenize(hyp)
    ra, ha = tokenize(ref, weaken_h=True), tokenize(hyp, weaken_h=True)
    matcher = SequenceMatcher(None, [u.key() for u in r], [u.key() for u in h], autojunk=False)
    items = []
    last_pron = None
    ops = matcher.get_opcodes()
    idx = -1
    while idx + 1 < len(ops):
        idx += 1
        tag, i1, i2, j1, j2 = ops[idx]
        if tag != "equal":
            item = _classify(r, h, ra, ha, i1, i2, j1, j2)
            if item["level"] == "fail" and any(u.kind != "H" for u in r[i1:i2] + h[j1:j2]):
                # Digits and Latin letters break the Hangul run, so liaison differs on the two sides
                # (닷컴이에요 [다커미에요] vs com이에요) and the matcher can split the span in the wrong
                # place. Try the span joined with the next few opcodes before calling it a failure.
                for end in range(idx + 1, min(idx + 5, len(ops))):
                    merged = _classify(r, h, ra, ha, i1, ops[end][2], j1, ops[end][4])
                    if merged["level"] != "fail":
                        item, idx = merged, end
                        break
            if item["level"] == "fail" and last_pron and last_pron[:3] == (len(items) - 1, i1, j1):
                items.pop()
                item = _item("fail", r[last_pron[3]:i2], h[last_pron[4]:j2], set(item["reasons"]))
            items.append(item)
            continue
        k, n = 0, i2 - i1
        while k < n:
            a, b = r[i1 + k], h[j1 + k]
            if a.kind == "NUM" and "." in a.text:
                items.append(_item("info", [a], [b], {"dot_unverified"}))
            if a.syl and a.text != b.text:
                start = k
                while k < n and r[i1 + k].syl and r[i1 + k].text != h[j1 + k].text:
                    k += 1
                R, H = r[i1 + start:i1 + k], h[j1 + start:j1 + k]
                rules = set().union(*(u.syl.rules for u in R + H if u.syl))
                items.append(_item("pass", R, H, {"pron"}, rules))
                last_pron = (len(items) - 1, i1 + k, j1 + k, i1 + start, j1 + start)
            else:
                k += 1
    if not any("dot_jeom" in it["reasons"] for it in items):
        for m in JEOM_IN_DIGITS.finditer(hyp):
            items.append({"level": "warn", "ref": "", "hyp": m.group(), "ref_pron": "", "hyp_pron": m.group(),
                          "reasons": ["dot_jeom"], "rules": []})
    verdict = "pass"
    for it in items:
        verdict = _worse(verdict, it["level"])
    counts = {lv: sum(it["level"] == lv for it in items) for lv in LEVELS}
    return {"verdict": verdict, "items": items, "counts": counts}


DOTTED = re.compile(r"(?<![\d.])([vV]?)(\d+)((?:\.\d+)+)(?!\.?\d)")


def prep(text: str, keep_digits: bool = False) -> tuple[str, list[str]]:
    """Rewrite dots inside numbers so a TTS engine says 쩜.

    Digits after the dot are read one by one: '3.14' -> '삼 쩜 일사', '0.05' -> '영 쩜 영오'.
    Versions (two or more dots, or a leading v) read every part after the first digit by
    digit with 0 as 공: '5.1.40' -> '오 쩜 일 쩜 사공', 'v5.1.34' -> '브이 오 쩜 일 쩜 삼사'.
    keep_digits gives '2쩜5'. Dates such as 2026.10.19 and short dates such as 10.21
    (two-digit month, two-digit day, no % after) are left alone and returned in the second value.
    """
    skipped: list[str] = []

    def repl(m: re.Match[str]) -> str:
        prefix, head, rest = m.groups()
        parts = [head] + rest[1:].split(".")
        long_date = len(parts) == 3 and len(head) == 4
        short_date = (len(parts) == 2 and len(head) == 2 and len(parts[1]) == 2 and 1 <= int(head) <= 12
                      and 1 <= int(parts[1]) <= 31 and not m.string[m.end():].lstrip().startswith("%"))
        if not prefix and (long_date or short_date):
            skipped.append(m.group())
            return m.group()
        if keep_digits:
            return prefix + DOT_OK.join(parts)
        version = bool(prefix) or len(parts) > 2
        words = [sino(int(head))[0]] + [digitwise(p)[1 if version else 0] for p in parts[1:]]
        return ("브이 " if prefix else "") + f" {DOT_OK} ".join(words)

    return DOTTED.sub(repl, text), skipped
