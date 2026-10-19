"""Rule-based Korean grapheme-to-phoneme conversion.

Implements the main rules of the Standard Pronunciation Rules (표준 발음법,
Part 2 of 표준어 규정). Each output syllable remembers which clauses changed
it, so a comparison can say *why* two spellings sound the same.

Only the Python standard library is used.
"""
from __future__ import annotations

from dataclasses import dataclass, field

CHO = list("ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ")
JUNG = list("ㅏㅐㅑㅒㅓㅔㅕㅖㅗㅘㅙㅚㅛㅜㅝㅞㅟㅠㅡㅢㅣ")
JONG = ["", "ㄱ", "ㄲ", "ㄳ", "ㄴ", "ㄵ", "ㄶ", "ㄷ", "ㄹ", "ㄺ", "ㄻ", "ㄼ", "ㄽ", "ㄾ",
        "ㄿ", "ㅀ", "ㅁ", "ㅂ", "ㅄ", "ㅅ", "ㅆ", "ㅇ", "ㅈ", "ㅊ", "ㅋ", "ㅌ", "ㅍ", "ㅎ"]

SPLIT = {"ㄳ": ("ㄱ", "ㅅ"), "ㄵ": ("ㄴ", "ㅈ"), "ㄶ": ("ㄴ", "ㅎ"), "ㄺ": ("ㄹ", "ㄱ"),
         "ㄻ": ("ㄹ", "ㅁ"), "ㄼ": ("ㄹ", "ㅂ"), "ㄽ": ("ㄹ", "ㅅ"), "ㄾ": ("ㄹ", "ㅌ"),
         "ㄿ": ("ㄹ", "ㅍ"), "ㅀ": ("ㄹ", "ㅎ"), "ㅄ": ("ㅂ", "ㅅ")}
# Representative final sounds (clauses 9-11).
REP = {"ㄲ": "ㄱ", "ㅋ": "ㄱ", "ㄳ": "ㄱ", "ㄺ": "ㄱ",
       "ㅅ": "ㄷ", "ㅆ": "ㄷ", "ㅈ": "ㄷ", "ㅊ": "ㄷ", "ㅌ": "ㄷ", "ㅎ": "ㄷ",
       "ㅍ": "ㅂ", "ㄿ": "ㅂ", "ㅄ": "ㅂ",
       "ㄵ": "ㄴ", "ㄶ": "ㄴ", "ㄼ": "ㄹ", "ㄽ": "ㄹ", "ㄾ": "ㄹ", "ㅀ": "ㄹ", "ㄻ": "ㅁ"}
REP_CLAUSE = {"ㄳ": "10", "ㄵ": "10", "ㄼ": "10", "ㄽ": "10", "ㄾ": "10", "ㅄ": "10",
              "ㄺ": "11", "ㄻ": "11", "ㄿ": "11", "ㄶ": "12", "ㅀ": "12", "ㅎ": "12"}
TENSE = {"ㄱ": "ㄲ", "ㄷ": "ㄸ", "ㅂ": "ㅃ", "ㅅ": "ㅆ", "ㅈ": "ㅉ"}
LAX = {v: k for k, v in TENSE.items()}
ASPIRATE = {"ㄱ": "ㅋ", "ㄷ": "ㅌ", "ㅂ": "ㅍ", "ㅈ": "ㅊ"}
NASAL = {"ㄱ": "ㅇ", "ㄷ": "ㄴ", "ㅂ": "ㅁ"}

# A non-initial 의 may be [의], [이] or, as the particle, [에] (clause 5, proviso 4).
WILD_UI = "ㅢ*"

RULE_NAMES = {
    "5": ("제5항 이중 모음", "clause 5 diphthongs"),
    "9": ("제9항 받침 대표음", "clause 9 representative finals"),
    "10": ("제10항 겹받침", "clause 10 double finals"),
    "11": ("제11항 겹받침", "clause 11 double finals"),
    "12": ("제12항 받침 ㅎ", "clause 12 final ㅎ"),
    "13": ("제13항 연음", "clause 13 liaison"),
    "14": ("제14항 겹받침 연음", "clause 14 double-final liaison"),
    "17": ("제17항 구개음화", "clause 17 palatalization"),
    "18": ("제18항 비음화", "clause 18 nasalization"),
    "19": ("제19항 ㄹ의 비음화", "clause 19 ㄹ to ㄴ"),
    "20": ("제20항 유음화", "clause 20 lateralization"),
    "23": ("제23항 경음화", "clause 23 tensing"),
    "24": ("제24항 경음화", "clause 24 tensing"),
    "25": ("제25항 경음화", "clause 25 tensing"),
}


@dataclass
class Syl:
    c: str
    v: str
    f: str
    src: str
    word_start: bool = False
    rules: set[str] = field(default_factory=set)

    def key(self):
        return (self.c, self.v, self.f)

    def text(self):
        v = "ㅢ" if self.v == WILD_UI else self.v
        return chr(0xAC00 + (CHO.index(self.c) * 21 + JUNG.index(v)) * 28 + JONG.index(self.f))


def is_syllable(ch: str) -> bool:
    return "가" <= ch <= "힣"


def decompose(ch: str, word_start: bool = False) -> Syl:
    code = ord(ch) - 0xAC00
    return Syl(CHO[code // 588], JUNG[(code % 588) // 28], JONG[code % 28], ch, word_start)


def _vowels(s: Syl) -> None:
    if s.v == "ㅖ" and s.c not in ("ㅇ", "ㄹ"):
        s.v = "ㅔ"; s.rules.add("5")
    elif s.v == "ㅕ" and s.c in ("ㅈ", "ㅉ", "ㅊ"):
        s.v = "ㅓ"; s.rules.add("5")
    elif s.v == "ㅢ":
        if s.c != "ㅇ":
            s.v = "ㅣ"; s.rules.add("5")
        elif not s.word_start:
            s.v = WILD_UI; s.rules.add("5")


def _final_alone(s: Syl) -> None:
    f = s.f
    r = "ㅂ" if (f == "ㄼ" and s.src == "밟") else REP.get(f, f)
    if r != f:
        s.rules.add(REP_CLAUSE.get(f, "9"))
    s.f = r


def _boundary(s: Syl, n: Syl | None) -> None:
    f = s.f
    if not f:
        return
    if n is None:
        _final_alone(s)
        return
    c2 = n.c
    if c2 == "ㅇ":
        if f == "ㅇ":
            return
        if f == "ㅎ":
            s.f = ""; s.rules.add("12"); return
        if f in ("ㄶ", "ㅀ"):
            s.f = ""; n.c = SPLIT[f][0]; s.rules |= {"12", "13"}; n.rules.add("13"); return
        if n.v == "ㅣ" and f in ("ㄷ", "ㅌ", "ㄾ"):
            if f == "ㄾ":
                s.f = "ㄹ"; n.c = "ㅊ"
            else:
                s.f = ""; n.c = "ㅈ" if f == "ㄷ" else "ㅊ"
            s.rules.add("17"); n.rules.add("17"); return
        if f in SPLIT:
            a, b = SPLIT[f]
            s.f = a; n.c = "ㅆ" if b == "ㅅ" else b
            s.rules.add("14"); n.rules.add("14"); return
        s.f = ""; n.c = f; s.rules.add("13"); n.rules.add("13"); return

    if f in ("ㅎ", "ㄶ", "ㅀ"):
        keep = "" if f == "ㅎ" else SPLIT[f][0]
        if c2 in ("ㄱ", "ㄷ", "ㅈ"):
            s.f = keep; n.c = ASPIRATE[c2]; s.rules.add("12"); n.rules.add("12"); return
        if c2 == "ㅅ":
            s.f = keep; n.c = "ㅆ"; s.rules.add("12"); n.rules.add("12"); return
        if c2 == "ㄴ":
            if f == "ㅀ":
                s.f = "ㄹ"; n.c = "ㄹ"; s.rules |= {"12", "20"}; n.rules.add("20")
            else:
                s.f = "ㄴ"; s.rules.add("12")
            return

    if c2 == "ㅎ":
        if f in SPLIT and SPLIT[f][1] in ASPIRATE:
            a, b = SPLIT[f]
            s.f = a; n.c = ASPIRATE[b]
        else:
            r = REP.get(f, f)
            if r in ASPIRATE:
                s.f = ""; n.c = "ㅊ" if f == "ㅈ" else ASPIRATE[r]
                if f == "ㄷ" and n.v == "ㅣ":
                    n.c = "ㅊ"; n.rules.add("17")
            else:
                if r != f:
                    s.rules.add(REP_CLAUSE.get(f, "9"))
                s.f = r
                return
        s.rules.add("12"); n.rules.add("12")
        return

    if f == "ㄺ" and c2 == "ㄱ":  # clause 11 proviso: 맑게 [말께]
        s.f = "ㄹ"; n.c = "ㄲ"; s.rules.add("11"); n.rules.add("23"); return
    r = "ㅂ" if (f == "ㄼ" and s.src == "밟") else REP.get(f, f)
    if r != f:
        s.rules.add(REP_CLAUSE.get(f, "9"))
    obstruent = r in ("ㄱ", "ㄷ", "ㅂ")
    if obstruent and c2 in ("ㄴ", "ㅁ"):
        r = NASAL[r]; s.rules.add("18")
    elif c2 == "ㄹ":
        if r in ("ㅁ", "ㅇ"):
            n.c = "ㄴ"; n.rules.add("19")
        elif obstruent:
            n.c = "ㄴ"; r = NASAL[r]; s.rules |= {"18", "19"}; n.rules.add("19")
        elif r == "ㄴ":
            r = "ㄹ"; s.rules.add("20")
    elif r == "ㄹ" and c2 == "ㄴ":
        n.c = "ㄹ"; n.rules.add("20")
    elif obstruent and c2 in TENSE:
        n.c = TENSE[c2]; n.rules.add("23")
    elif f in ("ㄵ", "ㄻ") and c2 in ("ㄱ", "ㄷ", "ㅅ", "ㅈ"):
        n.c = TENSE[c2]; n.rules.add("24")
    elif f in ("ㄼ", "ㄾ") and c2 in ("ㄱ", "ㄷ", "ㅅ", "ㅈ"):
        n.c = TENSE[c2]; n.rules.add("25")
    s.f = r


def apply_rules(syls: list[Syl]) -> list[Syl]:
    for s in syls:
        _vowels(s)
    for i, s in enumerate(syls):
        _boundary(s, syls[i + 1] if i + 1 < len(syls) else None)
    return syls


def g2p(text: str) -> str:
    """Pronunciation of a Hangul string, e.g. g2p('국물') == '궁물'.

    Spaces are ignored on purpose: speech recognizers space words differently
    from the script, so the comparison must not depend on spacing.
    """
    syls, word_start = [], True
    out = []
    for ch in text:
        if is_syllable(ch):
            syls.append(decompose(ch, word_start)); word_start = False
        else:
            word_start = True
            if not ch.isspace():
                out.append(("run", syls)); syls = []
                out.append(("raw", ch))
    out.append(("run", syls))
    parts = []
    for kind, val in out:
        if kind == "raw":
            parts.append(val)
        else:
            parts.append("".join(s.text() for s in apply_rules(val)))
    return "".join(parts)
