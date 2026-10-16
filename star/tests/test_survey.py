"""问卷：题型校验（单选 / 多选 / 打分表 / 其他填空）、答案展示、界面定制规则。"""
from django.test import SimpleTestCase

from star.content.levels import THEMES
from star.services import profile as svc

Q = svc._SURVEY_BY_KEY


class SurveyDefinitionTests(SimpleTestCase):

    def test_every_interest_has_a_theme_and_favorites(self):
        # 兴趣决定闯关主题包和引导对话的选项，缺一个学生端就会出错
        for o in Q['interest']['options']:
            self.assertIn(o['value'], THEMES)
            self.assertTrue(svc.FAVORITES.get(o['value']))

    def test_keys_unique_and_titles_first_person(self):
        keys = [q['key'] for q in svc.SURVEY]
        self.assertEqual(len(keys), len(set(keys)))
        for q in svc.SURVEY:
            self.assertNotIn('你', q['title'], q['key'])   # 题目统一用第一人称"我"

    def test_example_answers_are_valid(self):
        clean, err = svc.valid_survey(svc.example_answers())
        self.assertEqual(err, '')
        self.assertEqual(set(clean), {q['key'] for q in svc.SURVEY})


class SurveyValidationTests(SimpleTestCase):

    def test_multi_requires_at_least_one_known_value(self):
        for bad in ([], ['image', 'nope'], 'image'):
            _, err = svc.valid_survey(svc.example_answers(learn_style=bad))
            self.assertIn('第 3 题', err)

    def test_multi_is_deduplicated_in_question_order(self):
        clean, _ = svc.valid_survey(svc.example_answers(learn_style=['text', 'image', 'text']))
        self.assertEqual(clean['learn_style'], ['image', 'text'])

    def test_scale_requires_every_row(self):
        rows = svc.example_answers()['color_like']
        rows.pop('gray')
        _, err = svc.valid_survey(svc.example_answers(color_like=rows))
        self.assertIn('灰色', err)
        _, err = svc.valid_survey(svc.example_answers(color_like=dict(rows, gray=9)))
        self.assertIn('灰色', err)

    def test_other_text_kept_only_when_other_chosen(self):
        clean, _ = svc.valid_survey(svc.example_answers(
            coding_hard=['rules', 'other'], coding_hard_other='  打字太慢了  ' + 'x' * 30))
        self.assertEqual(clean['coding_hard_other'], ('打字太慢了  ' + 'x' * 30)[:svc.OTHER_MAX])
        clean, _ = svc.valid_survey(svc.example_answers(coding_hard=['rules'], coding_hard_other='忽略'))
        self.assertNotIn('coding_hard_other', clean)

    def test_answer_text(self):
        s = svc.example_answers(
            learn_style=['image', 'repeat'], icon_style='other', icon_style_other='小火车',
            shape_like={r['key']: 3 for r in Q['shape_like']['rows']} | {'star': 5},
        )
        self.assertEqual(svc.answer_text(Q['learn_style'], s), '看图片或图表、反复做很多遍')
        self.assertEqual(svc.answer_text(Q['icon_style'], s), '其他：小火车')
        self.assertIn('星形：很喜欢', svc.answer_text(Q['shape_like'], s))
        self.assertEqual(svc.answer_text(Q['learn_style'], {}), '')


class BuildUiTests(SimpleTestCase):

    def scores(self, qkey, value, **override):
        return {r['key']: value for r in Q[qkey]['rows']} | override

    def test_defaults_when_nothing_is_liked(self):
        ui = svc.build_ui(svc.example_answers(
            bg_color='any', color_like=self.scores('color_like', 3), shape_like=self.scores('shape_like', 2),
            ui_needs=self.scores('ui_needs', 'no')))
        self.assertEqual(ui['bg'], 'warm')
        self.assertEqual(ui['accent'], 'blue')
        self.assertEqual((ui['button'], ui['mark']), ('soft', '✓'))
        self.assertFalse(ui['font_adjust'] or ui['color_choice'])

    def test_picks_favourites(self):
        ui = svc.build_ui(svc.example_answers(
            bg_color='green', color_mix='like', icon_style='line',
            color_like=self.scores('color_like', 2, black=5, orange=5, pink=4),
            shape_like=self.scores('shape_like', 1, heart=5, circle=4),
            ui_needs=self.scores('ui_needs', 'any', font_size='some', choose_color='must')))
        self.assertEqual(ui['bg'], 'green')
        self.assertEqual(ui['accent'], 'orange')            # 黑色不当主色
        self.assertEqual(ui['liked_colors'], ['orange', 'pink'])
        self.assertEqual((ui['button'], ui['mark']), ('round', '♥'))
        self.assertEqual(ui['icon_style'], 'line')
        self.assertFalse(ui['calm'])
        self.assertTrue(ui['font_adjust'] and ui['color_choice'])

    def test_same_answers_same_ui(self):
        s = svc.example_answers()
        self.assertEqual(svc.build_ui(s), svc.build_ui(dict(s)))

    def test_presentation_prefer(self):
        self.assertEqual(svc.presentation_prefer({'learn_style': ['image', 'do']}), 'image')
        self.assertEqual(svc.presentation_prefer({'learn_style': ['text']}), 'text')
        self.assertEqual(svc.presentation_prefer({'learn_style': ['image', 'text']}), 'both')
        self.assertEqual(svc.presentation_prefer({}), 'both')
