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
kopron prep script.txt > script.tts.txt                   # 2.5 -> 이 쩜 오, 5.1.40 -> 오 쩜 일 쩜 사공 before TTS
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

The transcript may also write numbers as digits, Latin letters by name, or common units as abbreviations. These pass: `6개` = 여섯 개, `680` = 육백여든, `OK` = 오케이, `GB` = 기가, `%` = 퍼센트, `U.S.` = 미국 (or 유에스), `abc99.com` = 에이비씨 구구 닷컴.

The dot in a web address may be said 「닷」 or 「쩜」. Both pass, in Hangul (`닷컴` = `쩜컴`) and against the written address. 「점」 there is a `warn`, like a number dot.

### Flagged for listening (`warn`)

- **ㅐ/ㅔ (also ㅒ/ㅖ, ㅙ/ㅚ/ㅞ).** Clause 4 keeps them apart, but many speakers and most recognizers do not, so `샌 게` written as `센 게` cannot be judged from text.
- **Weakened ㅎ** (일하는 heard as 이라는). This is common in speech but it is not standard pronunciation.
- **A dot inside a number read as 「점」.** See below.

### The dot inside a number is 「쩜」

In this project the `.` inside a number is read **「쩜」**: `2.5` is 「이 쩜 오」, `v1.2` is 「브이 일 쩜 이」, `3.14` is 「삼 쩜 일사」.

Digits after the decimal point are read one by one, with 0 as 영: `0.38` is 「영 쩜 삼팔」, `3.05` is 「삼 쩜 영오」. A version number (two or more dots, or a leading `v`) reads every part after the first one digit by digit, with 0 as 공: `5.1.40` is 「오 쩜 일 쩜 사공」, `v5.1.34` is 「브이 오 쩜 일 쩜 삼사」. Reading 40 as 「사십」 there is a `fail`.

- If the transcript has 「점」 where the script means the dot (`2.5` → `이 점 오`, `3점1`, or the script says 쩜 and the transcript says 점), the result is `warn`.
- If the transcript keeps the digits (`2.5` → `2.5`), the text cannot show which word was said, and the result is `info`.
- `kopron prep` rewrites the script before TTS so the engine has no choice: `2.5` becomes `이 쩜 오`, `1.10.3` becomes `일 쩜 일공 쩜 삼`, and `--keep-digits` gives `2쩜5`. Dates such as `2026.10.19` and short dates such as `10.21` (two-digit month and day, no `%` after) are left alone and reported.

The national language regulations do not say how to read decimals, versions or web addresses. The National Institute of Korean Language (NIKL) said so on its Q&A board: decimals written in digits are not covered by the regulations ([2026-03-18](https://www.korean.go.kr/front/onlineQna/onlineQnaView.do?mn_id=216&qna_seq=328287)), the pronunciation of the decimal point is not regulated and the custom of each field should be followed ([2026-02-03](https://www.korean.go.kr/front/onlineQna/onlineQnaView.do?mn_id=216&qna_seq=327076)), and whether `41.10` ends in 일영 or 일공 is a matter of custom ([2025-06-26](https://www.korean.go.kr/front/onlineQna/onlineQnaView.do?mn_id=216&qna_seq=316996)). The Standard Korean Language Dictionary does have the word: 점(點) [점], "the decimal point of a decimal", as in 영 점 일 ([NIKL answer quoting it, 2024-11-07](https://www.korean.go.kr/front/onlineQna/onlineQnaView.do?mn_id=216&qna_seq=305492)); it has no entry for 쩜. Reading the digits after the point one by one is how primary-school mathematics teaches it (0.37 「영 점 삼칠」). 「쩜」, the version rule and 「닷」/「쩜」 for addresses are how these are actually said, and they are this project's rules.

### Known limits

- No morphology. Clause 15 (밭 아래 [바다래]) and clause 29 ㄴ-insertion (솜이불 [솜니불]) are not modeled, and neither are exceptions such as 의견란 [의견난].
- Spacing is ignored and liaison is applied across word boundaries. Recognizers space words differently from the script, so the comparison cannot depend on spacing.
- Vowel length (clauses 6 and 7) is not compared.
- A transcript is only text. A `pass` means "the text is consistent with correct speech", not "the audio was proven correct".
- Recognizers cannot tell 「점」 from 「쩜」. Whisper writes the digits (`2.2`). A Gemini model asked to write Hangul wrote 「점」 for all 16 clips with a known answer in one run and 「쩜」 for all 16 in the next. A 「점」 or 「쩜」 in a transcript is not evidence of what was said. See [How TTS engines read `.`](#how-tts-engines-read-).
- `kopron prep` leaves a short date alone only when both month and day have two digits (`10.21`). `3.14` or `5.18` cannot be told from decimals and are read as decimals. Write such dates out yourself (「시월 이십일일」).
- A transcript that writes `US` or `U.S.` passes against 「미국」, but it cannot show whether 「미국」 or 「유에스」 was said. Only `US`, `USA` and `UK` are known country abbreviations.
- Irregular month names (시월, 유월) do not match `10월`, `6월` in a transcript, and Latin spellings such as `Node.js` do not match a Hangul reading. These come out as `fail` and need a look.

## Getting transcripts

`tools/transcribe_mlx.py` transcribes audio with [mlx-whisper](https://github.com/ml-explore/mlx-examples) on Apple Silicon and writes files in the layout `kopron batch` expects:

```sh
uv run --with mlx-whisper tools/transcribe_mlx.py --out transcripts audio/*.m4a
kopron batch scripts/ transcripts/
```

It runs with `condition_on_previous_text=False`, so one misheard sentence does not leak into the next. It also drops segments that start after the last speech, where Whisper tends to invent words. The dropped text stays in `<name>-segments.json`. ffmpeg is required.

## How TTS engines read `.`

A test on 2026-10-21 with five engines: Gemini 3.8 Flash TTS on Vertex AI (voices Puck and Achernar), macOS `say` (Yuna), Edge TTS (`ko-KR-SunHiNeural`) and Qwen3-TTS 1.7B CustomVoice 8-bit (Sohee, local mlx). Eleven sentences were given in two forms, three takes each:

- **A, plain text**: `응답까지 2.2초 걸렸어요.`
- **B, written as spoken**: `kopron prep`, then numbers written out by hand: `응답까지 이 쩜 이 초 걸렸어요.`

Each clip was transcribed twice, by Whisper large-v3-turbo (`tools/transcribe_mlx.py`) and by Gemini 3.8 Flash asked to write only Hangul. One sentence contains a domain name and is not shown here.

**What the engines did with plain text (A).** 3/3 means three takes out of three. The correct readings are 「오 쩜 일 쩜 사공」 for `5.1.40`, 「브이 오 쩜 일 쩜 삼사」 for `v5.1.34` and 「미국」 for `U.S.`.

| Input | Gemini Puck | Gemini Achernar | macOS say Yuna | Edge SunHi | Qwen3 Sohee |
| --- | --- | --- | --- | --- | --- |
| `2.2초` `0.38초` `3.5%` | **쩜** (a person listened) | same as Puck | leans 쩜 | **쩜** (9/9, waveform match) | same as Puck |
| `5.1.40` | 40 could not be decided | same as Puck | a date: 「천구백사십 년 오월 일일」 | **「오 쩜 일 쩜 사공」** (3/3, waveform match) | same as Puck |
| `v5.1.34` | 「일」 dropped 1/3; 34 could not be decided | 「삼백사십사」 1/3; otherwise could not be decided | a date: 「천구백삼십사 년 오월 일일」 | leans 「삼십사」 (waveform) | garbled 1/3; otherwise could not be decided |
| `10.21` (a date) | a decimal: 「십 쩜 이일」 3/3 | 「시월 …」 as a date; a wrong day 1/3, another 1/3* | could not be decided | a decimal | a decimal 3/3 |
| sentence end `.` and `...` | not read, pause 0.4-0.7 s | not read, 0.3-0.6 s | not read, 0.2 s | not read, about 1 s | not read, 0.4-1.4 s |
| `A.I.` `U.S.` | 에이아이, 유에스 (not 미국) | same | same | an extra syllable after 에이아이 3/3 | an extra syllable 1/3 |
| `Node.js` | 노드제이에스 (dot not read) | same | same | same | same |

`say` gives the same audio for the same text, so its three takes are one recording. For Edge, the plain-text audio was compared with audio made from 「이 쩜 이」 and 「이 점 이」 (DTW over log-mel frames); it matched the 쩜 version in all 9 takes. `5.1.40` was checked the same way against audio made from 「…사공」 and 「…사십」: Edge matched 「사공」 in all 3 takes (distance about 0.6 against 4.8). The same check could not separate the Gemini and Qwen takes, which vary from take to take; for the dot in `2.2` and `3.5%` a person listened and heard 「쩜」.

The Gemini transcript cannot tell 「사공」 from 「사십」 either. It wrote 「사십」, 「사공」, 「사십」 for three identical `say` recordings, and 「사십」 for Edge clips whose waveform matches 「사공」.

**Writing it as spoken (B) helped but did not remove errors.** The B scripts for `5.1.40`, `v5.1.34` and `U.S.` were first written as 「사십」, 「삼십사」 and 「유에스」; they were corrected to 「사공」, 「삼사」 and 「미국」 and those clips were made again (3 sentences x 3 takes per engine). Counts are out of 33 clips (11 sentences x 3 takes):

| | Gemini Puck | Gemini Achernar | macOS say Yuna | Edge SunHi | Qwen3 Sohee |
| --- | --- | --- | --- | --- | --- |
| Both transcripts show an error | 1 | 2 | 0 | 0 | 1 |
| Only one transcript shows one | 3 | 3 | 13 | 6 | 8 |

With the text already spelled out, Achernar read 「이십일일」 as 「이십이일」 (2/3), Puck read it as 「이십일」 (1/3), and Qwen read 「브이」 as 「뷔」 (1/3, also in the first version). Many of the one-transcript cases are the Gemini transcript writing 「사십」 for 「사공」, which it also does for identical recordings (see above). So: run `kopron prep`, write numbers out, and still transcribe. The transcript cannot check 점 versus 쩜, so that part rests on writing 「쩜」 in the input.

**Listen.** One clip per engine, the plain-text sentences (A) in order:

| Engine | Clip |
| --- | --- |
| Gemini 3.8 Flash TTS, Puck | [gemini-puck.mp4](samples/dot-reading/gemini-puck.mp4) |
| Gemini 3.8 Flash TTS, Achernar | [gemini-achernar.mp4](samples/dot-reading/gemini-achernar.mp4) |
| macOS say, Yuna | [say-yuna.mp4](samples/dot-reading/say-yuna.mp4) |
| Edge TTS, SunHi | [edge-sunhi.mp4](samples/dot-reading/edge-sunhi.mp4) |
| Qwen3-TTS, Sohee | [qwen-sohee.mp4](samples/dot-reading/qwen-sohee.mp4) |

## Tests

```sh
python3 -m unittest -v
```

## License

MIT. See [LICENSE](LICENSE). The pronunciation rules are implemented in this repository and no third-party g2p library is used. mlx-whisper (MIT) is needed only for the optional transcription helper.

Sources: [표준어 규정 (law.go.kr)](https://www.law.go.kr/admRulInfoP.do?admRulSeq=2100000080512), [제2부 표준 발음법 (National Institute of Korean Language)](https://www.korean.go.kr/front/page/pageView.do?page_id=P000098&mn_id=95).
