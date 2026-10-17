"""
星语接口，挂在 /api/star/ 下。

学生端（登录即可）
    GET   me/                     画像状态；未完成时带上问卷或下一轮引导对话
    POST  survey/                 提交图形化问卷
    POST  dialogue/               回答一轮引导对话；最后一轮答完后生成画像（P1），等待教师确认
    GET   tasks/                  我的任务（只含已审核通过的）
    GET   tasks/<id>/             任务内容（去掉答案）+ 进度
    POST  tasks/<id>/hint/        取某一级提示
    POST  tasks/<id>/attempt/     提交作答，后端判定并记录
    POST  chat/                   对话助手（P3）

教师端（教师 / 管理员；教师只看自己团队里的学生）
    GET   teacher/learners/                     学生列表
    GET   teacher/learners/<uid>/               画像、任务、学习统计
    PATCH teacher/learners/<uid>/               修改层级 / 词表等，confirm=true 时确认画像
    POST  teacher/learners/<uid>/profile/       重新生成画像（P1）
    POST  teacher/learners/<uid>/tasks/         发起改造（P2，生成-校验-修复）
    POST  teacher/learners/<uid>/report/        学习报告（P4）
    GET   teacher/materials/                    素材库：关卡模板与入门题
    GET   teacher/assign/                       批量布置：我的团队与其中的学习者
    POST  teacher/assign/                       批量布置：一组素材 × 一组学生，用默认版本生成
    GET   teacher/tasks/<id>/                   审核页数据：内容、预览、校验日志
    PATCH teacher/tasks/<id>/                   修改文字（重新校验）
    DELETE teacher/tasks/<id>/                  删除任务
    POST  teacher/tasks/<id>/approve/           审核通过，内容锁定
    POST  teacher/tasks/<id>/regenerate/        重新生成（已有作答记录的任务不允许）
"""
from django.db.models import Max
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from judge.models import Team
from judge.permissions import _is_staff
from judge.services.judge_queue import RunQueueBusy

from .content.levels import LEVELS, THEMES
from .content.problems import PROBLEMS, get_problem, problem_row
from .models import AdaptedTask, LearnerProfile, StepAttempt
from .permissions import IsTeacherOrAdmin, can_view_learner, is_admin, visible_learner_ids
from .services import adapt, assistant, expressions, learning, llm, maze, profile as profile_svc, report
from .services.validators import LAYERS, reference_lines

def _busy():
    return Response({'detail': '评测机繁忙，请稍后再试'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)


def _llm_unavailable(err):
    return Response(
        {'detail': f'大模型接口调用失败（{err}）。请检查 .env 里的 LLM_API_URL / LLM_API_KEY / LLM_MODEL；'
                   '改过 .env 后要完全停掉后端再启动（自动重载不会重新读取）。', 'code': 'llm_unavailable'},
        status=status.HTTP_503_SERVICE_UNAVAILABLE,
    )


def _llm_missing():
    return Response(
        {'detail': '未配置大模型（.env 中的 LLM_API_KEY / LLM_API_URL / LLM_MODEL），'
                   '可以先选"使用默认版本"。', 'code': 'llm_not_configured'},
        status=status.HTTP_503_SERVICE_UNAVAILABLE,
    )


def _task_summary(task, with_progress=False):
    c = task.content or {}
    data = {
        'id': task.id,
        'title': c.get('title') or task.template,
        'template': task.template,
        'layer': task.layer,
        'kind': 'level' if task.layer == 'enlighten' else 'steps',
        'knowledge': c.get('knowledge') if task.layer == 'enlighten' else None,
        'status': task.status,
        'gen_count': task.gen_count,
        'sort_order': task.sort_order,
        'steps_total': learning.steps_total(task),
        'created_at': task.created_at,
        'approved_at': task.approved_at,
    }
    if with_progress:
        done = learning.done_steps(task)
        data['done_steps'] = sorted(done)
        data['done'] = len(done) >= data['steps_total'] > 0
    return data


# ═══════════════════════════ 学生端 ═══════════════════════════

class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        lp = LearnerProfile.objects.filter(user=request.user).first()
        data = {
            'status': lp.status if lp else 'new',
            'nickname': lp.nickname if lp else request.user.username,
            'layer': lp.layer if lp else '',
            'is_teacher': _is_staff(request.user),
        }
        if lp is None or lp.status == 'surveying':
            answered = bool(lp and lp.survey)
            data['survey'] = profile_svc.SURVEY
            data['survey_done'] = answered
            if answered:
                data['dialogue'] = profile_svc.dialogue_question(
                    lp.survey, len((lp.dialogue or {}).get('intro', [])), request.user.username)
        if lp:
            data['theme_key'] = (lp.profile or {}).get('theme_key', '')
        data['ui'] = _learner_ui(lp)
        return Response(data)


class SurveyView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        lp, _ = LearnerProfile.objects.get_or_create(user=request.user)
        if lp.status != 'surveying':
            return Response({'detail': '问卷已经填过了，需要重填请找老师'}, status=status.HTTP_409_CONFLICT)
        answers, err = profile_svc.valid_survey(request.data.get('answers'))
        if err:
            return Response({'detail': err}, status=status.HTTP_400_BAD_REQUEST)
        lp.survey = answers
        lp.dialogue = dict(lp.dialogue or {}, intro=[])
        lp.save()
        return Response({'dialogue': profile_svc.dialogue_question(answers, 0, request.user.username),
                         'ui': _learner_ui(lp)})


class DialogueView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        lp = LearnerProfile.objects.filter(user=request.user).first()
        if lp is None or not lp.survey or lp.status != 'surveying':
            return Response({'detail': '请先完成问卷'}, status=status.HTTP_400_BAD_REQUEST)
        intro = list((lp.dialogue or {}).get('intro', []))
        q = profile_svc.dialogue_question(lp.survey, len(intro), request.user.username)
        if q is None:
            return Response({'detail': '引导对话已经完成'}, status=status.HTTP_409_CONFLICT)
        answer = str(request.data.get('answer', '')).strip()[:30]
        if not answer:
            return Response({'detail': '请点一个选项，或者写一句话'}, status=status.HTTP_400_BAD_REQUEST)
        intro.append({'key': q['key'], 'question': q['ask'], 'answer': answer,
                      'via': 'option' if request.data.get('via') == 'option' else 'text'})
        lp.dialogue = dict(lp.dialogue or {}, intro=intro)

        nxt = profile_svc.dialogue_question(lp.survey, len(intro), request.user.username)
        if nxt is not None:
            lp.save(update_fields=['dialogue', 'updated_at'])
            return Response({'done': False, 'dialogue': nxt})

        prof, vocab, _log = profile_svc.generate_profile(lp)
        lp.profile, lp.vocabulary, lp.layer, lp.status = prof, vocab, prof['layer'], 'pending'
        lp.save()
        return Response({'done': True, 'status': lp.status, 'nickname': lp.nickname})


def _my_task(request, pk):
    task = AdaptedTask.objects.filter(pk=pk, student=request.user, status='approved').first()
    if task is None:
        raise NotFound('任务不存在')
    return task


class MyTasksView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        tasks = AdaptedTask.objects.filter(student=request.user, status='approved').order_by('sort_order', 'id')
        return Response([_task_summary(t, with_progress=True) for t in tasks])


class MyTaskDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        task = _my_task(request, pk)
        lp = LearnerProfile.objects.filter(user=request.user).first()
        nickname = lp.nickname if lp else request.user.username
        siblings = list(AdaptedTask.objects.filter(student=request.user, status='approved')
                        .order_by('sort_order', 'id').values_list('id', flat=True))
        idx = siblings.index(task.id)
        return Response({
            **_task_summary(task, with_progress=True),
            'content': learning.student_content(task, nickname),
            'next_task_id': siblings[idx + 1] if idx + 1 < len(siblings) else None,
            'position': idx + 1,
            'tasks_total': len(siblings),
        })


def _step_index(request, task):
    try:
        step = int(request.data.get('step', 0))
    except (TypeError, ValueError):
        step = -1
    if not 0 <= step < learning.steps_total(task):
        return None
    return step


class HintView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        task = _my_task(request, pk)
        step = _step_index(request, task)
        if step is None:
            return Response({'detail': '步骤不存在'}, status=status.HTTP_400_BAD_REQUEST)
        lp = LearnerProfile.objects.filter(user=request.user).first()
        return Response(learning.hint(task, step, request.data.get('level', 1),
                                      lp.nickname if lp else request.user.username))


class AttemptView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'run'       # 排序题会真的跑代码，与自定义运行同一档限流

    def post(self, request, pk):
        task = _my_task(request, pk)
        step = _step_index(request, task)
        if step is None:
            return Response({'detail': '步骤不存在'}, status=status.HTTP_400_BAD_REQUEST)
        answer = request.data.get('answer')
        if not isinstance(answer, dict):
            return Response({'detail': '作答格式不对'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            ok, result, stored = learning.judge(task, step, answer)
        except learning.BadAnswer as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except RunQueueBusy:
            return _busy()

        def _int(name, lo, hi):
            try:
                return max(lo, min(hi, int(request.data.get(name, 0))))
            except (TypeError, ValueError):
                return lo

        StepAttempt.objects.create(
            task=task, step_index=step, is_correct=ok, answer=stored,
            hint_level=_int('hint_level', 0, 3),
            duration_ms=_int('duration_ms', 0, 3_600_000),
        )
        done = learning.done_steps(task)
        return Response({
            'correct': ok, **result,
            'done_steps': sorted(done),
            'task_done': len(done) >= learning.steps_total(task),
        })


class ChatView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'star_ai'

    def post(self, request):
        lp = LearnerProfile.objects.filter(user=request.user).first()
        if lp is None:
            return Response({'detail': '请先完成问卷'}, status=status.HTTP_400_BAD_REQUEST)
        text = str(request.data.get('text', '')).strip()
        if not text:
            return Response({'detail': '请说一句话或点一个按钮'}, status=status.HTTP_400_BAD_REQUEST)
        task, step = None, None
        if request.data.get('task_id'):
            task = AdaptedTask.objects.filter(pk=request.data['task_id'], student=request.user,
                                              status='approved').first()
            if task is not None:
                step = _step_index(request, task)
        via = 'option' if request.data.get('via') == 'option' else 'text'
        return Response(assistant.reply(lp, text, task=task, step=step, via=via))


# ═══════════════════════════ 教师端 ═══════════════════════════

class TeacherBase(APIView):
    permission_classes = [IsAuthenticated, IsTeacherOrAdmin]

    def learner(self, request, uid):
        if not can_view_learner(request.user, uid):
            raise NotFound('学生不存在，或不在你的团队里')
        return get_object_or_404(LearnerProfile.objects.select_related('user'), user_id=uid)

    def task(self, request, pk):
        task = get_object_or_404(AdaptedTask.objects.select_related('student'), pk=pk)
        if not can_view_learner(request.user, task.student_id):
            raise NotFound('任务不存在')
        return task


def _survey_rows(lp):
    rows = []
    for q in profile_svc.SURVEY:
        v = (lp.survey or {}).get(q['key'])
        opt = next((o for o in q.get('options', []) if o['value'] == v), None)   # 单选题才有单个图标
        rows.append({'key': q['key'], 'title': q['title'], 'type': profile_svc.qtype(q), 'value': v,
                     'label': profile_svc.answer_text(q, lp.survey), 'icon': opt['icon'] if opt else ''})
    return rows


def _learner_ui(lp):
    """学生端界面设置：优先用画像里定下的；刚填完问卷、画像还没生成时按问卷现算。"""
    if lp is None:
        return dict(profile_svc.DEFAULT_UI)
    return (lp.profile or {}).get('ui') or profile_svc.build_ui(lp.survey)


def _learner_payload(lp):
    u = lp.user
    return {
        'user_id': u.id,
        'username': u.username,
        'real_name': getattr(getattr(u, 'profile', None), 'real_name', ''),
        'nickname': lp.nickname,
        'layer': lp.layer,
        'status': lp.status,
        'survey': _survey_rows(lp),
        'ui': _learner_ui(lp),
        'profile': lp.profile,
        'vocabulary': lp.vocabulary,
        'expressions': [dict(e, active=expressions.is_active(e)) for e in lp.expressions or []],
        'intro_dialogue': (lp.dialogue or {}).get('intro', []),
        'assistant_dialogue': (lp.dialogue or {}).get('assistant', [])[-20:],
        'confirmed_at': lp.confirmed_at,
        'updated_at': lp.updated_at,
    }


class LearnerListView(TeacherBase):
    def get(self, request):
        ids = list(visible_learner_ids(request.user))
        rows = []
        for lp in LearnerProfile.objects.filter(user_id__in=ids).select_related('user').order_by('user__username'):
            s = report.learner_stats(lp.user)['summary']
            rows.append({
                'user_id': lp.user_id, 'username': lp.user.username, 'nickname': lp.nickname,
                'layer': lp.layer, 'status': lp.status,
                'tasks_total': s['tasks_total'], 'tasks_done': s['tasks_done'], 'avg_hint': s['avg_hint'],
                'pending_tasks': AdaptedTask.objects.filter(student=lp.user).exclude(status='approved').count(),
            })
        return Response({'learners': rows, 'llm_configured': llm.is_configured()})


class LearnerDetailView(TeacherBase):
    def get(self, request, uid):
        lp = self.learner(request, uid)
        tasks = AdaptedTask.objects.filter(student=lp.user).order_by('sort_order', 'id')
        return Response({
            'learner': _learner_payload(lp),
            'tasks': [_task_summary(t, with_progress=True) for t in tasks],
            'stats': report.learner_stats(lp.user),
            'themes': {k: {'name': v['name'], 'hero': v['hero']} for k, v in THEMES.items()},
            'llm_configured': llm.is_configured(),
        })

    def patch(self, request, uid):
        lp = self.learner(request, uid)
        d = request.data
        prof = dict(lp.profile or {})

        if 'layer' in d:
            if d['layer'] not in LAYERS:
                return Response({'detail': '层级只能是启蒙层或入门层'}, status=status.HTTP_400_BAD_REQUEST)
            lp.layer = prof['layer'] = d['layer']
        if 'nickname' in d:
            prof['nickname'] = str(d['nickname']).strip()[:10]
        if 'interests' in d:
            items = d['interests'] if isinstance(d['interests'], list) else []
            prof['interests'] = [str(x).strip()[:8] for x in items if str(x).strip()][:3]
        if 'theme_key' in d:
            if d['theme_key'] not in THEMES:
                return Response({'detail': '主题不存在'}, status=status.HTTP_400_BAD_REQUEST)
            prof['theme_key'] = d['theme_key']
        if 'communication' in d and isinstance(d['communication'], dict):
            comm = dict(prof.get('communication') or {})
            for k in ('pronoun_reversal', 'echolalia'):
                if k in d['communication']:
                    comm[k] = bool(d['communication'][k])
            if 'notes' in d['communication']:
                comm['notes'] = str(d['communication']['notes'])[:60]
            prof['communication'] = comm
        if 'presentation' in d and isinstance(d['presentation'], dict):
            pres = dict(prof.get('presentation') or {})
            if d['presentation'].get('prefer') in ('image', 'text', 'both'):
                pres['prefer'] = d['presentation']['prefer']
            if d['presentation'].get('step_size') in ('small', 'normal'):
                pres['step_size'] = d['presentation']['step_size']
            prof['presentation'] = pres
        if 'vocabulary' in d:
            vocab = []
            for v in d['vocabulary'] if isinstance(d['vocabulary'], list) else []:
                word = str((v or {}).get('word', '')).strip()[:10]
                meaning = str((v or {}).get('meaning', '')).strip()[:10]
                if word and meaning:
                    vocab.append({'word': word, 'meaning': meaning})
            lp.vocabulary = vocab[:20]
        if 'expressions' in d:
            expressions.teacher_update(lp, d['expressions'])

        lp.profile = prof
        if d.get('confirm'):
            if not lp.layer:
                return Response({'detail': '请先选择层级'}, status=status.HTTP_400_BAD_REQUEST)
            lp.status, lp.confirmed_by, lp.confirmed_at = 'confirmed', request.user, timezone.now()
        lp.save()
        return Response({'learner': _learner_payload(lp)})


class ProfileRegenerateView(TeacherBase):
    def post(self, request, uid):
        lp = self.learner(request, uid)
        if not lp.survey:
            return Response({'detail': '学生还没有填问卷'}, status=status.HTTP_400_BAD_REQUEST)
        prof, vocab, _log = profile_svc.generate_profile(lp)
        lp.profile, lp.vocabulary, lp.layer = prof, vocab, prof['layer']
        if lp.status == 'confirmed':
            lp.status, lp.confirmed_by, lp.confirmed_at = 'pending', None, None
        lp.save()
        return Response({'learner': _learner_payload(lp)})


class MaterialsView(TeacherBase):
    def get(self, request):
        levels = []
        for lv in LEVELS:
            sol = maze.shortest_solution(lv)
            levels.append({'key': lv['key'], 'title': lv['title'], 'knowledge': lv['knowledge'],
                           'slots': lv['slots'], 'shortest': len(sol) if sol else None})
        problems = []
        for p in PROBLEMS:
            row = problem_row(p['slug'])
            problems.append({'key': p['slug'], 'title': p['title'], 'knowledge': p['knowledge'],
                             'demo': bool(p.get('demo')), 'has_default': bool(p.get('default_steps')),
                             'problem_id': row.id if row else None})
        return Response({'levels': levels, 'problems': problems, 'llm_configured': llm.is_configured()})


class TaskCreateView(TeacherBase):
    def post(self, request, uid):
        lp = self.learner(request, uid)
        if not lp.layer:
            return Response({'detail': '请先在画像里确定层级'}, status=status.HTTP_400_BAD_REQUEST)
        key = str(request.data.get('material', '')).strip()
        mode = 'template' if request.data.get('mode') == 'template' else 'llm'
        problem = None
        if lp.layer == 'enlighten':
            if key not in {lv['key'] for lv in LEVELS}:
                return Response({'detail': '启蒙层只能选关卡模板'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            if get_problem(key) is None:
                return Response({'detail': '入门层只能选入门题'}, status=status.HTTP_400_BAD_REQUEST)
            problem = problem_row(key)
            if problem is None:
                return Response({'detail': '题库里还没有这道题，请先运行 manage.py seed_star'},
                                status=status.HTTP_400_BAD_REQUEST)
        if mode == 'llm' and not llm.is_configured():
            return _llm_missing()

        order = AdaptedTask.objects.filter(student=lp.user).aggregate(m=Max('sort_order'))['m'] or 0
        task = AdaptedTask.objects.create(student=lp.user, layer=lp.layer, template=key, problem=problem,
                                          sort_order=order + 1, created_by=request.user)
        try:
            adapt.generate(task, mode=mode)
        except adapt.MaterialError as e:
            task.delete()
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except adapt.LLMUnavailable as e:
            task.delete()
            return _llm_unavailable(e)
        except RunQueueBusy:
            task.delete()
            return _busy()
        return Response(_task_detail(task), status=status.HTTP_201_CREATED)


ASSIGN_MAX_LEARNERS = 60
ASSIGN_MAX_MATERIALS = 21


class AssignView(TeacherBase):
    """
    批量布置：教师选一个团队里的若干学生、若干素材，一次发下去。

    · 只用默认版本（关卡按学生的兴趣主题包套主题，入门题用 default_steps），不调用大模型——
      批量调用大模型要排很久；需要个性化改造的学生，仍在学生详情页单独发起；
    · 默认版本本身已通过全部规则校验，approve=true（默认）时直接审核通过、学生立即能看到；
      approve=false 时留作草稿，逐个到审核页看过再通过；
    · 素材按层级分发：关卡只发给启蒙层学生，入门题只发给入门层学生；
      学生已经有同一素材的任务（生成失败的除外）时跳过，不重复布置。
    """

    def get(self, request):
        visible = set(visible_learner_ids(request.user))
        teams = Team.objects.filter(is_active=True).order_by('-created_at')
        if not is_admin(request.user):
            teams = teams.filter(creator=request.user)
        profiles = {lp.user_id: lp for lp in LearnerProfile.objects.filter(user_id__in=visible).select_related('user')}
        have = {}
        for uid, key in (AdaptedTask.objects.filter(student_id__in=list(profiles)).exclude(status='failed')
                         .values_list('student_id', 'template')):
            have.setdefault(uid, set()).add(key)
        out = []
        for team in teams.prefetch_related('memberships'):
            learners = []
            for m in team.memberships.all():
                lp = profiles.get(m.user_id)
                if lp is None:
                    continue
                learners.append({'user_id': lp.user_id, 'username': lp.user.username, 'nickname': lp.nickname,
                                 'layer': lp.layer, 'status': lp.status,
                                 'templates': sorted(have.get(lp.user_id, ()))})
            learners.sort(key=lambda x: x['username'])
            out.append({'id': team.id, 'name': team.name, 'learners': learners})
        return Response({'teams': out})

    def post(self, request):
        d = request.data
        uids, keys = d.get('learners'), d.get('materials')
        if not isinstance(uids, list) or not uids:
            return Response({'detail': '请至少选一名学生'}, status=status.HTTP_400_BAD_REQUEST)
        if not isinstance(keys, list) or not keys:
            return Response({'detail': '请至少选一项任务'}, status=status.HTTP_400_BAD_REQUEST)
        if len(uids) > ASSIGN_MAX_LEARNERS or len(keys) > ASSIGN_MAX_MATERIALS:
            return Response({'detail': f'一次最多 {ASSIGN_MAX_LEARNERS} 名学生、{ASSIGN_MAX_MATERIALS} 项任务'},
                            status=status.HTTP_400_BAD_REQUEST)
        level_keys = {lv['key'] for lv in LEVELS}
        keys = list(dict.fromkeys(str(k).strip() for k in keys))      # 去重，保留教师选的顺序
        unknown = [k for k in keys if k not in level_keys and get_problem(k) is None]
        if unknown:
            return Response({'detail': f'素材不存在：{"、".join(unknown)}'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            uids = list(dict.fromkeys(int(u) for u in uids))
        except (TypeError, ValueError):
            return Response({'detail': '学生编号不对'}, status=status.HTTP_400_BAD_REQUEST)
        visible = set(visible_learner_ids(request.user))
        if any(u not in visible for u in uids):
            return Response({'detail': '有学生不在你的团队里'}, status=status.HTTP_403_FORBIDDEN)

        approve = d.get('approve', True) is not False
        rows = {k: problem_row(k) for k in keys if k not in level_keys}
        results, created_total = [], 0
        for lp in LearnerProfile.objects.filter(user_id__in=uids).select_related('user').order_by('user__username'):
            created, skipped = self._assign_one(request.user, lp, keys, level_keys, rows, approve)
            created_total += len(created)
            results.append({'user_id': lp.user_id, 'username': lp.user.username, 'nickname': lp.nickname,
                            'created': created, 'skipped': skipped})
        return Response({'results': results, 'created_total': created_total, 'approved': approve},
                        status=status.HTTP_201_CREATED if created_total else status.HTTP_200_OK)

    @staticmethod
    def _assign_one(teacher, lp, keys, level_keys, rows, approve):
        if not lp.layer:
            return [], [{'template': k, 'reason': '还没有确定层级'} for k in keys]
        created, skipped = [], []
        have = set(AdaptedTask.objects.filter(student=lp.user).exclude(status='failed')
                   .values_list('template', flat=True))
        order = AdaptedTask.objects.filter(student=lp.user).aggregate(m=Max('sort_order'))['m'] or 0
        for key in keys:
            is_level = key in level_keys
            if is_level != (lp.layer == 'enlighten'):
                skipped.append({'template': key, 'reason': '层级不对'})
                continue
            if key in have:
                skipped.append({'template': key, 'reason': '已经有这项任务'})
                continue
            if not is_level and rows.get(key) is None:
                skipped.append({'template': key, 'reason': '题库里还没有这道题，请先运行 seed_star'})
                continue
            task = AdaptedTask.objects.create(student=lp.user, layer=lp.layer, template=key,
                                              problem=None if is_level else rows[key],
                                              sort_order=order + 1, created_by=teacher)
            try:
                adapt.generate(task, mode='template')
            except adapt.MaterialError as e:
                task.delete()
                skipped.append({'template': key, 'reason': str(e)})
                continue
            except RunQueueBusy:
                task.delete()
                skipped.append({'template': key, 'reason': '评测机繁忙，请稍后再试'})
                continue
            order += 1
            if approve and task.status == 'draft':
                task.status, task.approved_by, task.approved_at = 'approved', teacher, timezone.now()
                task.save(update_fields=['status', 'approved_by', 'approved_at', 'updated_at'])
            created.append({'id': task.id, 'template': key, 'title': (task.content or {}).get('title') or key,
                            'status': task.status})
        return created, skipped


class ReportView(TeacherBase):
    def post(self, request, uid):
        lp = self.learner(request, uid)
        audience = 'parent' if request.data.get('audience') == 'parent' else 'teacher'
        return Response(dict(report.make_report(lp, audience), audience=audience))


def _task_detail(task):
    lp = task.student.star_profile
    content = task.content or {}
    data = {
        **_task_summary(task, with_progress=True),
        'student': {'user_id': task.student_id, 'username': task.student.username, 'nickname': lp.nickname,
                    'ui': _learner_ui(lp), 'avoid_pronouns': adapt.avoid_pronouns(task)},
        'content': content,
        'validation_log': task.validation_log,
        'locked': task.status == 'approved',
        'has_attempts': task.attempts.exists(),
    }
    try:
        chk = adapt.check_content(task, content)
        data['check'] = chk.as_dict()
    except adapt.MaterialError as e:
        data['check'] = {'format_ok': False, 'rules_ok': False, 'errors': [str(e)]}
    if data['check']['rules_ok']:
        data['preview'] = learning.student_content(task, lp.nickname)
    if task.layer == 'enlighten' and data['check']['format_ok']:
        try:
            sol = maze.shortest_solution(content)
        except (KeyError, TypeError, ValueError):
            sol = None
        data['solution'] = sol
    else:
        material = get_problem(task.template)
        data['reference_code'] = material['code'] if material else ''
        data['reference_lines'] = reference_lines(material['code']) if material else []
    return data


class TaskDetailView(TeacherBase):
    def get(self, request, pk):
        return Response(_task_detail(self.task(request, pk)))

    def patch(self, request, pk):
        task = self.task(request, pk)
        if task.status == 'approved':
            return Response({'detail': '已通过的任务已锁定；如需修改，请先重新生成'},
                            status=status.HTTP_409_CONFLICT)
        content = request.data.get('content')
        if not isinstance(content, dict):
            return Response({'detail': 'content 必须是 JSON 对象'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            chk = adapt.check_content(task, content)
        except adapt.MaterialError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        run_no = 1 + max((e.get('run', 0) for e in task.validation_log or []), default=0)
        task.content = content
        task.status = 'draft' if chk.ok else 'failed'
        task.validation_log = (task.validation_log or []) + [{
            'run': run_no, 'mode': 'edit', 'attempt': 1, 'ok': chk.ok, 'errors': chk.errors,
            'at': timezone.now().isoformat(),
        }]
        task.save()
        return Response(_task_detail(task))

    def delete(self, request, pk):
        self.task(request, pk).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class TaskApproveView(TeacherBase):
    def post(self, request, pk):
        task = self.task(request, pk)
        chk = adapt.check_content(task, task.content)
        if not chk.ok:
            return Response({'detail': '还有校验没通过的地方', 'errors': chk.errors},
                            status=status.HTTP_400_BAD_REQUEST)
        task.status, task.approved_by, task.approved_at = 'approved', request.user, timezone.now()
        task.save(update_fields=['status', 'approved_by', 'approved_at', 'updated_at'])
        return Response(_task_detail(task))


class TaskRegenerateView(TeacherBase):
    def post(self, request, pk):
        task = self.task(request, pk)
        if task.attempts.exists():
            return Response({'detail': '这个任务已有作答记录，为保留学习数据不能重新生成；可以新建一个任务'},
                            status=status.HTTP_409_CONFLICT)
        mode = 'template' if request.data.get('mode') == 'template' else 'llm'
        if mode == 'llm' and not llm.is_configured():
            return _llm_missing()
        try:
            adapt.generate(task, mode=mode)
        except adapt.MaterialError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except adapt.LLMUnavailable as e:
            return _llm_unavailable(e)
        except RunQueueBusy:
            return _busy()
        return Response(_task_detail(task))
