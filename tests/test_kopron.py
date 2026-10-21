import unittest

from kopron import compare, g2p, prep


def levels(ref, hyp):
    result = compare(ref, hyp)
    return result["verdict"], [(i["level"], i["ref"], i["hyp"], i["reasons"]) for i in result["items"]]


class Required(unittest.TestCase):
    def test_liaison_hug_e_passes(self):
        verdict, items = levels("훅에 넣자", "후계 넣자")
        self.assertEqual(verdict, "pass")
        self.assertEqual(items, [("pass", "훅에", "후계", ["pron"])])

    def test_nasalization_gungmul_passes(self):
        self.assertEqual(levels("국물", "궁물")[0], "pass")

    def test_dot_read_as_jeom_warns(self):
        verdict, items = levels("2.5배", "이 점 오 배")
        self.assertEqual(verdict, "warn")
        self.assertIn("dot_jeom", items[0][3])

    def test_dot_read_as_jjeom_passes(self):
        self.assertEqual(levels("2.5배", "이 쩜 오 배")[0], "pass")

    def test_real_word_change_fails(self):
        verdict, items = levels("넣자", "놓자")
        self.assertEqual(verdict, "fail")
        self.assertEqual(items[0][:3], ("fail", "넣", "놓"))


class Rules(unittest.TestCase):
    CASES = {
        "훅에": "후게", "국물": "궁물", "신라": "실라", "칼날": "칼랄", "굳이": "구지", "같이": "가치",
        "국화": "구콰", "놓고": "노코", "좋아": "조아", "많아": "마나", "싫어": "시러", "닭을": "달글",
        "값을": "갑쓸", "국밥": "국빱", "넣자": "너차", "담력": "담녁", "협력": "혐녁", "앉히다": "안치다",
        "맑게": "말께", "밟다": "밥따", "여덟": "여덜", "굳히다": "구치다", "놓는": "논는", "희망": "히망",
        "넋이": "넉씨", "읽다": "익따", "젊지": "점찌", "맞히다": "마치다", "가져": "가저", "닳는": "달른",
    }

    def test_g2p_examples(self):
        for word, sound in self.CASES.items():
            with self.subTest(word=word):
                self.assertEqual(g2p(word), sound)

    def test_spacing_does_not_matter(self):
        self.assertEqual(levels("훅에넣자", "후계 넣 자")[0], "pass")


class Allowed(unittest.TestCase):
    def test_particle_ui_as_e(self):
        self.assertEqual(levels("나의 꿈", "나에 꿈")[0], "pass")

    def test_non_initial_ui_as_i(self):
        self.assertEqual(levels("회의 결과", "회이 결과")[0], "pass")

    def test_ye_after_consonant(self):
        self.assertEqual(levels("시계", "시게")[0], "pass")

    def test_tensing_needs_no_spelling(self):
        self.assertEqual(levels("할 거야", "할 꺼야")[0], "pass")

    def test_digits_for_words(self):
        self.assertEqual(levels("여섯 개", "6개")[0], "pass")
        self.assertEqual(levels("이천삼백 명", "2300명")[0], "pass")
        self.assertEqual(levels("육백여든 개", "680개")[0], "pass")

    def test_letter_names(self):
        self.assertEqual(levels("오케이", "OK")[0], "pass")
        self.assertEqual(levels("AI", "ai")[0], "pass")
        self.assertEqual(levels("18기가", "18GB")[0], "pass")


class Flagged(unittest.TestCase):
    def test_ae_e_is_a_warning(self):
        verdict, items = levels("돈이 샌 게", "돈이 센 게")
        self.assertEqual(verdict, "warn")
        self.assertEqual(items[0][3], ["ae_e"])

    def test_weak_h_is_a_warning(self):
        verdict, items = levels("일하는", "이라는")
        self.assertEqual(verdict, "warn")
        self.assertEqual(items[0][3], ["h_weak"])

    def test_jjeom_spelled_but_jeom_heard(self):
        self.assertEqual(levels("이 쩜 오", "이 점 오")[0], "warn")

    def test_digits_on_both_sides_cannot_prove_the_dot(self):
        self.assertEqual(levels("2.5배", "2.5배")[0], "info")

    def test_script_jeom_but_jjeom_heard_passes(self):
        self.assertEqual(levels("3점1", "삼 쩜 일")[0], "pass")

    def test_jeom_between_digits_in_transcript(self):
        self.assertEqual(levels("삼 쩜 일", "3점1")[0], "warn")

    def test_extra_and_missing_words_fail(self):
        self.assertEqual(levels("고맙습니다", "고맙습니다 감사합니다")[0], "fail")
        self.assertEqual(levels("정말 고맙습니다", "고맙습니다")[0], "fail")

    def test_failed_span_keeps_its_left_neighbour(self):
        verdict, items = levels("짜. 이름", "짝 이름")
        self.assertEqual(verdict, "fail")
        self.assertEqual(items[0][1:3], ("짜이", "짝이"))

    def test_wrong_number_fails(self):
        self.assertEqual(levels("여섯 개", "7개")[0], "fail")


class Readings(unittest.TestCase):
    def test_version_parts_digit_by_digit(self):
        self.assertEqual(levels("오 쩜 일 쩜 사공 판", "5.1.40 판")[0], "pass")
        self.assertEqual(levels("5.1.40 판", "오 쩜 일 쩜 사공 판")[0], "pass")
        self.assertEqual(levels("오 쩜 일 쩜 사공 판", "오 쩜 일 쩜 사십 판")[0], "fail")
        self.assertEqual(levels("브이 오 쩜 일 쩜 삼사에서", "V5.1.34에서")[0], "pass")

    def test_country_abbreviation(self):
        self.assertEqual(levels("미국 회사가", "U.S. 회사가")[0], "pass")
        self.assertEqual(levels("U.S. 회사가", "미국 회사가")[0], "pass")
        self.assertEqual(levels("U.S. 회사가", "유에스 회사가")[0], "pass")
        self.assertEqual(levels("미국 회사가", "유에스 회사가")[0], "fail")

    def test_dotted_letters_stay_letters(self):
        self.assertEqual(levels("에이아이 도구", "A.I. 도구")[0], "pass")

    def test_web_address_dot_dat_or_jjeom(self):
        self.assertEqual(levels("에이비씨 구구 닷컴", "에이비씨 구구 쩜컴")[0], "pass")
        self.assertEqual(levels("에이비씨 구구 쩜컴", "에이비씨 구구 닷컴")[0], "pass")
        self.assertEqual(levels("에이비씨 구구 닷컴", "abc99.com")[0], "pass")
        self.assertEqual(levels("abc99.com", "에이비씨 구구 쩜컴")[0], "pass")
        self.assertEqual(levels("주소는 에이비씨 구구 닷컴이에요.", "주소는 abc99.com이에요.")[0], "pass")
        self.assertEqual(levels("주소는 에이비씨 구구 닷컴이에요.", "주소는 abc98.com이에요.")[0], "fail")

    def test_web_address_dot_as_jeom_warns(self):
        self.assertEqual(levels("에이비씨 구구 닷컴", "에이비씨 구구 점컴")[0], "warn")
        self.assertEqual(levels("abc99.com", "에이비씨 구구 점컴")[0], "warn")

    def test_dat_outside_an_address_is_still_a_word(self):
        self.assertEqual(levels("닷새", "쩜새")[0], "fail")


class Prep(unittest.TestCase):
    def test_decimal(self):
        self.assertEqual(prep("2.5배")[0], "이 쩜 오배")
        self.assertEqual(prep("3.14")[0], "삼 쩜 일사")

    def test_decimal_digits_one_by_one_with_yeong(self):
        self.assertEqual(prep("0.38초")[0], "영 쩜 삼팔초")
        self.assertEqual(prep("3.05")[0], "삼 쩜 영오")
        self.assertEqual(prep("12.5%")[0], "십이 쩜 오%")

    def test_version(self):
        self.assertEqual(prep("v1.2")[0], "브이 일 쩜 이")
        self.assertEqual(prep("1.10.3")[0], "일 쩜 일공 쩜 삼")

    def test_version_parts_after_the_first_digit_by_digit(self):
        self.assertEqual(prep("5.1.40 판")[0], "오 쩜 일 쩜 사공 판")
        self.assertEqual(prep("v5.1.34에서")[0], "브이 오 쩜 일 쩜 삼사에서")
        self.assertEqual(prep("10.2.1")[0], "십 쩜 이 쩜 일")

    def test_short_dates_are_left_alone(self):
        self.assertEqual(prep("발표는 10.21에"), ("발표는 10.21에", ["10.21"]))
        self.assertEqual(prep("10.25%")[0], "십 쩜 이오%")

    def test_keep_digits(self):
        self.assertEqual(prep("2.5배", keep_digits=True)[0], "2쩜5배")

    def test_dates_are_left_alone(self):
        self.assertEqual(prep("2026.10.19"), ("2026.10.19", ["2026.10.19"]))

    def test_sentence_dot_untouched(self):
        self.assertEqual(prep("3. 다음")[0], "3. 다음")


if __name__ == "__main__":
    unittest.main()
