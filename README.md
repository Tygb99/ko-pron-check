# ko-pron-check

[한국어](README.ko.md)

Check Korean TTS audio against its script **by pronunciation, not by spelling**.

A common way to test TTS is to transcribe the audio with speech recognition (STT) and diff it against the script. In Korean that diff is full of false alarms, because recognizers write what they *hear*:

| Script | Transcript | What happened |
| --- | --- | --- |
| 훅에 넣자 | 후계 넣자 | Both are pronounced [후게 너차]. Correct speech. |
| 국물 | 궁물 | Standard pronunciation is [궁물]. Correct speech. |
| 2.5배 | 이 점 오 배 | The dot was read 「점」. This project says it should be 「쩜」. |
| 넣자 | 놓자 | A different word. A real error. |

`kopron` turns both sides into standard pronunciation and compares that. Differences that come only from the Standard Pronunciation Rules pass. The clause that explains each one is shown, so only real differences are left for you to listen to.

## Install

There are no dependencies (Python 3.9+, standard library only).

```sh
uv tool install git+https://github.com/Tygb99/ko-pron-check   # or: pipx install git+...
kopron compare "훅에 넣자" "후계 넣자"
```

You can also run it from a clone without installing: `python3 -m kopron ...`.

## Use

```sh
kopron compare "국물이 끓어요" "궁무리 끄러요"          # one pair
kopron compare --ref-file script.txt --hyp-file stt.txt --json
kopron batch scripts/ transcripts/ --json-out report.json   # scripts/s1.txt <-> transcripts/s1.txt
kopron g2p "닭을 굳이"                                   # -> 달글구지
kopron prep script.txt > script.tts.txt                   # 2.5 -> 이 쩜 오 before TTS
```

```
$ kopron compare "돈이 샌 게 훅에 넣자" "돈이 센 게 후계 넣자"
verdict: warn  pass=1 info=0 warn=1 fail=0
  WARN  샌 -> 센  ㅐ/ㅔ(ㅒ/ㅖ, ㅙ/ㅚ/ㅞ) 차이. ...
  PASS  훅에 -> 후계 [후게]/[후게]  표준 발음이 같음 (제5항 이중 모음, 제13항 연음)
```

Use `--lang en` for English messages.

Each difference gets a level:

| Level | Meaning | Exit code |
| --- | --- | --- |
| `pass` | Same standard pronunciation, digits vs. words, letter names, units | 0 |
| `info` | Cannot be decided from text (the transcript kept `2.5`, so 점 vs 쩜 is unknown) | 0 |
| `warn` | Probably fine but listen: ㅐ/ㅔ, weakened ㅎ, a dot read as 「점」 | 0 (`--strict`: 2) |
| `fail` | Different sound: wrong word, missing or extra words | 1 |

## The rules

The rules come from the Standard Pronunciation Rules (표준 발음법), which are Part 2 of the Korean Standard Language Regulations (표준어 규정, Ministry of Culture, Sports and Tourism notice 2017-13). Clause numbers below are clauses of that part.

### Accepted as the same sound (`pass`)

| Clause | Rule | Examples |
| --- | --- | --- |
| 5, proviso 1 | 져/쪄/쳐 are said [저/쩌/처] | 가져 [가저] |
| 5, proviso 2 | ㅖ after a consonant other than ㅇ, ㄹ may be [ㅔ] | 시계 [시게], so 후계 = [후게] |
| 5, proviso 3 | ㅢ after a consonant is [ㅣ] | 희망 [히망] |
| 5, proviso 4 | Non-initial 의 may be [이], the particle 의 may be [에] | 회의 [회이], 나의 [나에] |
| 9 | Finals are said as ㄱ, ㄷ or ㅂ before a consonant and at the end | 부엌 [부억], 옷 [옫], 앞 [압] |
| 10, 11 | Double finals keep one sound | 넋 [넉], 여덟 [여덜], 밟다 [밥따], 닭 [닥], 맑게 [말께] |
| 12 | Final ㅎ: aspiration, ㅅ to ㅆ, ㄴ, or silent before a vowel | 놓고 [노코], 국화 [구콰], 놓는 [논는], 좋아 [조아], 많아 [마나] |
| 13 | A final moves to the next vowel-initial syllable (liaison) | 훅에 [후게], 옷이 [오시] |
| 14 | Of a double final only the second moves (ㅅ becomes ㅆ) | 넋이 [넉씨], 값을 [갑쓸], 닭을 [달글] |
| 17 | ㄷ, ㅌ before 이 become ㅈ, ㅊ (palatalization) | 굳이 [구지], 같이 [가치], 굳히다 [구치다] |
| 18 | ㄱ, ㄷ, ㅂ before ㄴ, ㅁ become ㅇ, ㄴ, ㅁ (nasalization) | 국물 [궁물], 닫는 [단는], 밥물 [밤물] |
| 19 | ㄹ after ㅁ, ㅇ (and ㄱ, ㅂ) is [ㄴ] | 담력 [담녁], 강릉 [강능], 협력 [혐녁] |
| 20 | ㄴ next to ㄹ becomes [ㄹ] (lateralization) | 신라 [실라], 칼날 [칼랄], 닳는 [달른] |
| 23 | ㄱ, ㄷ, ㅂ, ㅅ, ㅈ after ㄱ, ㄷ, ㅂ finals are tensed | 국밥 [국빱], 읽다 [익따] |
| 24-28, 30 | Tensing that depends on word structure (stems, 관형사형 -ㄹ, compounds, 사이시옷) | 신고 [신꼬], 할 거야 [할꺼야], 김밥 [김빱] |

The tool does no morphological analysis, so for clauses 24-28 and 30 it accepts a plain or tense consonant at the start of a syllable that follows a final consonant. Both spellings pass.

The transcript may also write numbers as digits, Latin letters by name, or common units as abbreviations. These pass: `6개` = 여섯 개, `680` = 육백여든, `OK` = 오케이, `GB` = 기가, `%` = 퍼센트.

### Flagged for listening (`warn`)

- **ㅐ/ㅔ (also ㅒ/ㅖ, ㅙ/ㅚ/ㅞ).** Clause 4 keeps them apart, but many speakers and most recognizers do not, so `샌 게` written as `센 게` cannot be judged from text.
- **Weakened ㅎ** (일하는 heard as 이라는). This is common in speech but it is not standard pronunciation.
- **A dot inside a number read as 「점」.** See below.

### The dot inside a number is 「쩜」

In this project the `.` inside a number is read **「쩜」**: `2.5` is 「이 쩜 오」, `v1.2` is 「브이 일 쩜 이」, `3.14` is 「삼 쩜 일사」.

- If the transcript has 「점」 where the script means the dot (`2.5` → `이 점 오`, `3점1`, or the script says 쩜 and the transcript says 점), the result is `warn`.
- If the transcript keeps the digits (`2.5` → `2.5`), the text cannot show which word was said, and the result is `info`.
- `kopron prep` rewrites the script before TTS so the engine has no choice: `2.5` becomes `이 쩜 오`, versions become `일 쩜 십 쩜 삼`, and `--keep-digits` gives `2쩜5`. Date-like `2026.10.19` is left alone and reported.

The national language regulations do not say how to read decimals. The National Institute of Korean Language answered this on its Q&A board on 2026-03-18: [소수점 이하의 수 읽기](https://www.korean.go.kr/front/onlineQna/onlineQnaView.do?mn_id=216&qna_seq=328287). 「쩜」 is how the dot is actually said, and it is this project's rule.

### Known limits

- No morphology. Clause 15 (밭 아래 [바다래]) and clause 29 ㄴ-insertion (솜이불 [솜니불]) are not modeled, and neither are exceptions such as 의견란 [의견난].
- Spacing is ignored and liaison is applied across word boundaries. Recognizers space words differently from the script, so the comparison cannot depend on spacing.
- Vowel length (clauses 6 and 7) is not compared.
- A transcript is only text. A `pass` means "the text is consistent with correct speech", not "the audio was proven correct".

## Getting transcripts

`tools/transcribe_mlx.py` transcribes audio with [mlx-whisper](https://github.com/ml-explore/mlx-examples) on Apple Silicon and writes files in the layout `kopron batch` expects:

```sh
uv run --with mlx-whisper tools/transcribe_mlx.py --out transcripts audio/*.m4a
kopron batch scripts/ transcripts/
```

It runs with `condition_on_previous_text=False`, so one misheard sentence does not leak into the next. It also drops segments that start after the last speech, where Whisper tends to invent words. The dropped text stays in `<name>-segments.json`. ffmpeg is required.

## Tests

```sh
python3 -m unittest -v
```

## License

MIT. See [LICENSE](LICENSE). The pronunciation rules are implemented in this repository and no third-party g2p library is used. mlx-whisper (MIT) is needed only for the optional transcription helper.

Sources: [표준어 규정 (law.go.kr)](https://www.law.go.kr/admRulInfoP.do?admRulSeq=2100000080512), [제2부 표준 발음법 (National Institute of Korean Language)](https://www.korean.go.kr/front/page/pageView.do?page_id=P000098&mn_id=95).
