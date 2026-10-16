"""
团队 / 作业 / 提交可见性 API 测试。
运行（无需 MySQL）：
    DB_ENGINE=sqlite SECRET_KEY=test python manage.py test judge.tests.test_team
"""
import io
from datetime import timedelta

import openpyxl
from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from judge.models import (
    Assignment, AssignmentProblem, Problem, Submission, Tag, Team, TeamMembership, UserProfile,
)


def make_user(username, role='student', **profile):
    user = User.objects.create_user(username=username, password='pass1234')
    UserProfile.objects.create(user=user, role=role, **profile)
    return user


def submit(user, problem, status, when=None):
    sub = Submission.objects.create(user=user, problem=problem, code='int main(){}', status=status)
    if when is not None:
        Submission.objects.filter(pk=sub.pk).update(submitted_at=when)
    return sub


class TeamTestBase(TestCase):
    def setUp(self):
        self.teacher = make_user('teacher', role='teacher')
        self.other_teacher = make_user('teacher2', role='teacher')
        self.alice = make_user('alice', real_name='爱丽丝', student_id='2023001')
        self.bob = make_user('bob', real_name='鲍勃', student_id='2023002')
        self.outsider = make_user('eve')

        self.team = Team.objects.create(name='一班', creator=self.teacher, invite_code='ABCD1234')
        TeamMembership.objects.create(team=self.team, user=self.alice, remark='A同学')
        TeamMembership.objects.create(team=self.team, user=self.bob)

        self.dp = Tag.objects.create(name='动态规划')
        self.graph = Tag.objects.create(name='图论')
        self.p1 = Problem.objects.create(title='P1', description='d', input_desc='i', output_desc='o',
                                         sample_input='1', sample_output='1', difficulty='入门', is_published=True)
        self.p2 = Problem.objects.create(title='P2', description='d', input_desc='i', output_desc='o',
                                         sample_input='1', sample_output='1', difficulty='普及-', is_published=True)
        self.p3 = Problem.objects.create(title='P3', description='d', input_desc='i', output_desc='o',
                                         sample_input='1', sample_output='1', difficulty='普及-', is_published=True)
        self.p1.tags.add(self.dp)
        self.p2.tags.add(self.dp, self.graph)

        self.client = APIClient()

    def as_user(self, user):
        self.client.force_authenticate(user)
        return self.client


class MemberVisibilityTests(TeamTestBase):
    def test_plain_member_can_read_announcements_and_assignments(self):
        # 回归：此前普通成员访问公告/作业返回 403，导致学生团队页空白
        Assignment.objects.create(team=self.team, title='第一周', created_by=self.teacher)
        Assignment.objects.create(team=self.team, title='草稿', created_by=self.teacher, is_active=False)
        c = self.as_user(self.bob)
        self.assertEqual(c.get(f'/api/teams/{self.team.id}/announcements/').status_code, 200)
        r = c.get(f'/api/teams/{self.team.id}/assignments/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual([a['title'] for a in r.data], ['第一周'])   # 草稿不可见

    def test_outsider_is_forbidden(self):
        c = self.as_user(self.outsider)
        self.assertEqual(c.get(f'/api/teams/{self.team.id}/announcements/').status_code, 403)
        self.assertEqual(c.get(f'/api/teams/{self.team.id}/rank/').status_code, 403)

    def test_other_teacher_cannot_view_dashboard(self):
        c = self.as_user(self.other_teacher)
        self.assertEqual(c.get(f'/api/teams/{self.team.id}/dashboard/').status_code, 403)
        self.assertEqual(c.get(f'/api/teams/{self.team.id}/students/{self.alice.id}/').status_code, 403)

    def test_member_cannot_post_announcement(self):
        c = self.as_user(self.bob)
        r = c.post(f'/api/teams/{self.team.id}/announcements/', {'title': 'x'}, format='json')
        self.assertEqual(r.status_code, 403)


class TeamRankTests(TeamTestBase):
    def test_rank_with_ties_and_my_rank(self):
        submit(self.alice, self.p1, 'AC')
        submit(self.alice, self.p1, 'AC')      # 同题重复 AC 只算一次
        submit(self.bob, self.p2, 'AC')
        r = self.as_user(self.bob).get(f'/api/teams/{self.team.id}/rank/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual([x['rank'] for x in r.data], [1, 1])
        self.assertTrue(any(x['is_me'] and x['total_ac'] == 1 for x in r.data))

        teams = self.as_user(self.alice).get('/api/teams/').data
        self.assertEqual(teams[0]['my_rank'], 1)
        self.assertEqual(teams[0]['my_ac'], 1)


class DashboardTests(TeamTestBase):
    def test_difficulty_columns_and_time_range(self):
        old = timezone.now() - timedelta(days=60)
        submit(self.alice, self.p1, 'AC', when=old)
        submit(self.alice, self.p2, 'WA')
        submit(self.alice, self.p2, 'AC')
        c = self.as_user(self.teacher)

        r = c.get(f'/api/teams/{self.team.id}/dashboard/')
        self.assertEqual(r.status_code, 200)
        alice = next(x for x in r.data['ranking'] if x['user_id'] == self.alice.id)
        self.assertEqual(alice['total_ac'], 2)
        self.assertEqual(alice['by_diff']['入门'], 1)
        self.assertEqual(alice['by_diff']['普及-'], 1)
        self.assertEqual(alice['total_submit'], 3)
        self.assertEqual(alice['ac_rate'], 66.7)
        self.assertEqual(alice['rank'], 1)
        self.assertEqual(len(r.data['diff_levels']), 8)

        r = c.get(f'/api/teams/{self.team.id}/dashboard/', {'range': 'month'})
        alice = next(x for x in r.data['ranking'] if x['user_id'] == self.alice.id)
        self.assertEqual(alice['total_ac'], 1)   # 60 天前的 AC 不在本月内
        self.assertEqual(alice['total_submit'], 2)

        day = (timezone.localtime(old)).date().isoformat()
        r = c.get(f'/api/teams/{self.team.id}/dashboard/', {'range': 'custom', 'start': day, 'end': day})
        alice = next(x for x in r.data['ranking'] if x['user_id'] == self.alice.id)
        self.assertEqual(alice['total_ac'], 1)
        self.assertEqual(alice['by_diff']['入门'], 1)

    def test_captain_is_read_only_viewer(self):
        TeamMembership.objects.filter(team=self.team, user=self.bob).update(role='captain')
        c = self.as_user(self.bob)
        r = c.get(f'/api/teams/{self.team.id}/dashboard/')
        self.assertEqual(r.status_code, 200)
        self.assertFalse(r.data['can_manage'])
        self.assertEqual(c.get(f'/api/teams/{self.team.id}/requests/').status_code, 403)

    def test_export_xlsx(self):
        submit(self.alice, self.p1, 'AC')
        r = self.as_user(self.teacher).get(f'/api/teams/{self.team.id}/dashboard/export/', {'range': 'week'})
        self.assertEqual(r.status_code, 200)
        ws = openpyxl.load_workbook(io.BytesIO(r.content)).active
        self.assertEqual(ws.cell(1, 6).value, '总AC')
        self.assertEqual(ws.max_row, 3)


class StudentDetailTests(TeamTestBase):
    def test_knowledge_drilldown(self):
        submit(self.alice, self.p1, 'WA')
        submit(self.alice, self.p1, 'AC')
        submit(self.alice, self.p2, 'TLE')
        submit(self.alice, self.p3, 'NT')     # NT 不算有效尝试
        r = self.as_user(self.teacher).get(f'/api/teams/{self.team.id}/students/{self.alice.id}/')
        self.assertEqual(r.status_code, 200)
        tags = {t['tag']: t for t in r.data['knowledge']}
        self.assertEqual(set(tags), {'动态规划', '图论'})
        self.assertEqual(r.data['knowledge'][0]['tag'], '图论')   # 未 AC 比例最高的排最前
        dp = tags['动态规划']
        self.assertEqual((dp['ac_count'], dp['tried_count']), (1, 2))
        p1 = next(p for p in dp['problems'] if p['problem_id'] == self.p1.id)
        self.assertEqual(p1['submits_to_ac'], 2)
        p2 = next(p for p in dp['problems'] if p['problem_id'] == self.p2.id)
        self.assertEqual(p2['last_status'], 'TLE')
        self.assertEqual(r.data['member']['tried_count'], 2)
        self.assertEqual(r.data['member']['total_submit'], 4)


class AssignmentTests(TeamTestBase):
    def setUp(self):
        super().setUp()
        now = timezone.now()
        self.asgn = Assignment.objects.create(
            team=self.team, title='作业1', created_by=self.teacher,
            start_at=now - timedelta(days=7), deadline=now - timedelta(days=1),
        )
        AssignmentProblem.objects.create(assignment=self.asgn, problem=self.p1, sort_order=0)
        AssignmentProblem.objects.create(assignment=self.asgn, problem=self.p2, sort_order=1)
        submit(self.alice, self.p1, 'AC', when=now - timedelta(days=3))   # 按时
        submit(self.alice, self.p2, 'AC', when=now)                        # 补交
        submit(self.bob, self.p1, 'WA', when=now - timedelta(days=3))     # 尝试

    def test_student_sees_own_states(self):
        r = self.as_user(self.alice).get(f'/api/teams/{self.team.id}/assignments/')
        states = [p['state'] for p in r.data[0]['problems']]
        self.assertEqual(states, ['ontime', 'late'])

    def test_matrix(self):
        r = self.as_user(self.teacher).get(f'/api/teams/{self.team.id}/assignments/{self.asgn.id}/matrix/')
        self.assertEqual(r.status_code, 200)
        first, second = r.data['rows']
        self.assertEqual(first['user_id'], self.alice.id)
        self.assertEqual((first['ontime'], first['late']), (1, 1))
        self.assertEqual(second['cells'][0], {'state': 'tried', 'attempts': 1})
        self.assertEqual([c['done_count'] for c in r.data['columns']], [1, 1])

        r = self.as_user(self.teacher).get(f'/api/teams/{self.team.id}/assignments/{self.asgn.id}/matrix/export/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self.as_user(self.bob).get(
            f'/api/teams/{self.team.id}/assignments/{self.asgn.id}/matrix/').status_code, 403)

    def test_create_validates_window(self):
        c = self.as_user(self.teacher)
        r = c.post(f'/api/teams/{self.team.id}/assignments/', {
            'title': 'x', 'start_at': '2026-05-02T10:00', 'deadline': '2026-05-01T10:00',
        }, format='json')
        self.assertEqual(r.status_code, 400)
        r = c.post(f'/api/teams/{self.team.id}/assignments/', {
            'title': 'x', 'start_at': '2026-05-01T10:00', 'deadline': '2026-05-02T10:00',
            'problem_ids': [self.p2.id, self.p1.id, self.p2.id],
        }, format='json')
        self.assertEqual(r.status_code, 201)
        self.assertEqual([p['id'] for p in r.data['problems']], [self.p2.id, self.p1.id])


class ImportTests(TeamTestBase):
    def test_import_handles_numeric_ids_and_short_rows(self):
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(['学号', '姓名', '专业', '年级'])
        ws.append([2023101.0, '张三', '计科', '2023级'])
        ws.append([2023102, '李四'])            # 缺少专业 / 年级列
        ws.append([None, None, None, None])     # 空行跳过
        ws.append(['2023101', '张三'])          # 文件内重复
        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)
        buf.name = 'students.xlsx'

        r = self.as_user(self.teacher).post(f'/api/teams/{self.team.id}/import-students/', {'file': buf})
        self.assertEqual(r.status_code, 200)
        self.assertEqual((r.data['success'], r.data['failed']), (2, 1))
        self.assertTrue(User.objects.filter(username='2023101').exists())
        self.assertTrue(User.objects.get(username='2023102').profile.must_change_password)


class SubmissionCodeVisibilityTests(TeamTestBase):
    def setUp(self):
        super().setUp()
        self.sub = submit(self.alice, self.p1, 'AC')

    def test_code_visibility(self):
        """本人、教师可见；其他学生、未登录不可见（教师范围以 permissions.can_view_submission_code 为准）。"""
        url = f'/api/submissions/{self.sub.id}/'
        self.assertEqual(self.as_user(self.alice).get(url).data['code'], 'int main(){}')
        self.assertEqual(self.as_user(self.teacher).get(url).data['code'], 'int main(){}')

        data = self.as_user(self.bob).get(url).data      # 同队其他学生看不到
        self.assertEqual(data['code'], '')
        self.assertFalse(data['can_view_code'])
        self.assertEqual(data['user_id'], self.alice.id)

        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(url).data['code'], '')

    def test_list_never_contains_code(self):
        r = self.as_user(self.bob).get('/api/submissions/', {'all': 1})
        self.assertEqual(r.status_code, 200)
        self.assertNotIn('code', r.data['results'][0])
