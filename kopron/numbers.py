"""Ways a number, a Latin letter run or a symbol can be read aloud in Korean."""
from __future__ import annotations

import itertools
import re

DIGITS = "영일이삼사오육칠팔구"
NATIVE_ONES = ["", "하나", "둘", "셋", "넷", "다섯", "여섯", "일곱", "여덟", "아홉"]
NATIVE_ATTR = {1: ["한"], 2: ["두"], 3: ["세", "석", "서"], 4: ["네", "넉", "너"]}
NATIVE_TENS = ["", "열", "스물", "서른", "마흔", "쉰", "예순", "일흔", "여든", "아흔"]
LETTERS = {"a": ["에이"], "b": ["비"], "c": ["씨", "시"], "d": ["디"], "e": ["이"], "f": ["에프"],
           "g": ["지"], "h": ["에이치"], "i": ["아이"], "j": ["제이"], "k": ["케이"], "l": ["엘"],
           "m": ["엠"], "n": ["엔"], "o": ["오"], "p": ["피"], "q": ["큐"], "r": ["알"], "s": ["에스"],
           "t": ["티"], "u": ["유"], "v": ["브이"], "w": ["더블유"], "x": ["엑스"], "y": ["와이"],
           "z": ["지", "제트"]}
SYMBOLS = {"%": ["퍼센트", "프로"]}
UNIT_WORDS = {"kb": ["킬로바이트", "킬로"], "mb": ["메가바이트", "메가"], "gb": ["기가바이트", "기가"],
              "tb": ["테라바이트", "테라"], "km": ["킬로미터", "킬로"], "kg": ["킬로그램", "킬로"],
              "cm": ["센티미터", "센티"], "mm": ["밀리미터", "밀리"], "ml": ["밀리리터", "밀리"]}
DOT_OK = "쩜"
DOT_WRONG = "점"
LIMIT = 400


def _sino4(n: int) -> str:
    out = ""
    for value, name in ((1000, "천"), (100, "백"), (10, "십")):
        d = n // value % 10
        if d:
            out += ("" if d == 1 else DIGITS[d]) + name
    if n % 10:
        out += DIGITS[n % 10]
    return out


def sino(n: int) -> list[str]:
    if n == 0:
        return ["영", "공"]
    groups, units, i = [], ["", "만", "억", "조", "경"], 0
    while n > 0:
        g = n % 10000
        if g:
            groups.append(_sino4(g) + units[i])
        n //= 10000
        i += 1
    text = "".join(reversed(groups))
    out = [text]
    if text.startswith("만"):
        out.append("일" + text)
    return out


def native(n: int) -> list[str]:
    if not 1 <= n <= 99:
        return []
    tens, ones = divmod(n, 10)
    if ones == 0:
        return [NATIVE_TENS[tens]] + (["스무"] if tens == 2 else [])
    base = NATIVE_TENS[tens]
    return [base + NATIVE_ONES[ones]] + [base + a for a in NATIVE_ATTR.get(ones, [])]


def digitwise(s: str) -> list[str]:
    return ["".join(DIGITS[int(d)] for d in s), "".join("공" if d == "0" else DIGITS[int(d)] for d in s)]


def integer_readings(s: str) -> list[str]:
    n = int(s)
    out = sino(n) + native(n)
    if n >= 100 and n % 100:
        head = n - n % 100
        out += [h + t for h in sino(head) for t in native(n % 100)]
    if len(s) >= 3 or s.startswith("0"):
        out += digitwise(s)
    return list(dict.fromkeys(out))


def number_readings(token: str) -> list[tuple[str, bool]]:
    """Readings of a digit token as (hangul, uses_wrong_dot).

    '2.5' -> ('이쩜오', False), ('이점오', True), ...
    """
    token = token.replace(",", "") if re.fullmatch(r"\d{1,3}(,\d{3})+", token) else token
    if "." not in token:
        return [(r, False) for r in integer_readings(token)]
    head, *rest = token.split(".")
    choices = [sino(int(head))]
    for part in rest:
        choices.append(list(dict.fromkeys(digitwise(part) + sino(int(part)))))
    out = []
    for dot in (DOT_OK, DOT_WRONG):
        for combo in itertools.islice(itertools.product(*choices), LIMIT):
            out.append((dot.join(combo), dot == DOT_WRONG))
    return out


def latin_readings(token: str) -> list[str]:
    letters = [LETTERS.get(ch, [ch]) for ch in token.lower()]
    spelled = ["".join(p) for p in itertools.islice(itertools.product(*letters), LIMIT)]
    return UNIT_WORDS.get(token.lower(), []) + spelled
