"""
星语 —— 面向孤独症学习者的大模型编程学伴。

只新增 4 张表，用户、题目、测试点、评测机全部复用平台现有的：

    LearnerProfile  每名学生一条：问卷、画像、个人词表、表达记忆、对话记录、教师确认状态
    AdaptedTask     大模型改造出的个体化任务（启蒙层关卡 / 入门层分步任务），审核通过后锁定
    StepAttempt     每一次作答，卡片闯关与分步学习共用
    LLMCallLog      每一次大模型调用，测试报告的数据来源
"""
from django.contrib.auth.models import User
from django.db import models

from judge.models import Problem

LAYER_CHOICES = [
    ('enlighten', '启蒙层'),
    ('intro', '入门层'),
]


class LearnerProfile(models.Model):
    """学习者画像。对话记录也暂存在这里（dialogue 字段），不单独建表。"""

    STATUS_CHOICES = [
        ('surveying', '填写中'),
        ('pending', '待教师确认'),
        ('confirmed', '已确认'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='star_profile', verbose_name='学生')
    layer = models.CharField('层级', max_length=10, choices=LAYER_CHOICES, blank=True, default='')
    survey = models.JSONField('问卷结果', default=dict, blank=True)
    profile = models.JSONField('画像', default=dict, blank=True)
    vocabulary = models.JSONField('个人词表', default=list, blank=True)
    # 个人表达记忆：[{text, intent, status, votes, hits, learned_at, last_at}]，见 services/expressions.py
    expressions = models.JSONField('表达记忆', default=list, blank=True)
    # {'intro': [引导对话的问答], 'assistant': [对话助手的最近若干轮]}
    dialogue = models.JSONField('对话记录', default=dict, blank=True)
    status = models.CharField('教师确认状态', max_length=10, choices=STATUS_CHOICES, default='surveying')
    confirmed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name='+', verbose_name='确认教师')
    confirmed_at = models.DateTimeField('确认时间', null=True, blank=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '学习者画像'
        verbose_name_plural = verbose_name

    def __str__(self):
        return f'{self.user.username}（{self.get_layer_display() or "未定层级"}）'

    @property
    def nickname(self):
        """系统称呼学生统一用昵称；没填过就用用户名。"""
        return (self.profile or {}).get('nickname') or self.user.username


class AdaptedTask(models.Model):
    """
    改造结果。content 的结构见 services/validators.py：
        启蒙层 —— 关卡 JSON（网格、起点、终点、障碍、可用卡片、卡槽数、主题）
        入门层 —— 分步任务 JSON（3–6 步，每步含三级提示与知识点标签）

    学生端只能看到 status=approved 的任务；通过后内容锁定，教师要改必须重新生成，
    重新生成会退回草稿——学生端看到的内容因此始终是教师确认过的同一份。
    """

    STATUS_CHOICES = [
        ('draft', '草稿'),
        ('approved', '已通过'),
        ('failed', '生成失败'),
    ]

    problem = models.ForeignKey(Problem, on_delete=models.CASCADE, null=True, blank=True,
                                related_name='star_tasks', verbose_name='原题')
    # 素材编号：关卡模板为 L1…，入门题为 content/problems.py 里的 slug
    template = models.CharField('素材编号', max_length=40, blank=True, default='')
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='star_tasks', verbose_name='学生')
    layer = models.CharField('层级', max_length=10, choices=LAYER_CHOICES)
    content = models.JSONField('任务内容', default=dict, blank=True)
    status = models.CharField('状态', max_length=10, choices=STATUS_CHOICES, default='draft', db_index=True)
    gen_count = models.IntegerField('生成次数', default=0)
    validation_log = models.JSONField('校验日志', default=list, blank=True)
    sort_order = models.IntegerField('排序', default=0)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='+', verbose_name='发起教师')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='+', verbose_name='审核教师')
    approved_at = models.DateTimeField('审核时间', null=True, blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '改造任务'
        verbose_name_plural = verbose_name
        ordering = ['sort_order', 'id']

    def __str__(self):
        return f'{self.student.username} · {self.content.get("title") or self.template}'


class StepAttempt(models.Model):
    """一次作答。卡片闯关的关卡只有一步（step_index=0），answer 里记程序、结果与卡片数。"""

    task = models.ForeignKey(AdaptedTask, on_delete=models.CASCADE, related_name='attempts', verbose_name='任务')
    step_index = models.IntegerField('步骤序号')
    hint_level = models.IntegerField('提示等级', default=0)   # 0–3，作答时已用到的最高提示等级
    is_correct = models.BooleanField('是否正确', default=False)
    duration_ms = models.IntegerField('用时(毫秒)', default=0)
    answer = models.JSONField('作答内容', default=dict, blank=True)
    created_at = models.DateTimeField('作答时间', auto_now_add=True)

    class Meta:
        verbose_name = '作答记录'
        verbose_name_plural = verbose_name
        ordering = ['created_at', 'id']
        indexes = [models.Index(fields=['task', 'step_index'])]


class LLMCallLog(models.Model):
    """每次大模型调用一条。消融实验的格式合格率、重试次数、耗时、token 都从这里统计。"""

    PURPOSE_CHOICES = [
        ('P1', '画像生成'),
        ('P2', '任务改造'),
        ('P3', '对话辅导'),
        ('P4', '学习报告'),
        ('P5', '意图识别'),
        ('P6', '任务推荐'),
    ]

    purpose = models.CharField('用途', max_length=2, choices=PURPOSE_CHOICES, db_index=True)
    request = models.JSONField('输入', default=dict)
    response = models.TextField('输出', blank=True, default='')
    duration_ms = models.IntegerField('耗时(毫秒)', default=0)
    prompt_tokens = models.IntegerField('输入 token', default=0)
    completion_tokens = models.IntegerField('输出 token', default=0)
    total_tokens = models.IntegerField('token 数', default=0)
    passed = models.BooleanField('是否通过校验', null=True, blank=True)
    # {'format_ok': bool, 'rules_ok': bool, 'errors': [...]}
    checks = models.JSONField('校验详情', default=dict, blank=True)
    attempt = models.IntegerField('重试序号', default=1)
    error = models.TextField('调用错误', blank=True, default='')
    tag = models.CharField('实验标记', max_length=60, blank=True, default='', db_index=True)
    task = models.ForeignKey(AdaptedTask, on_delete=models.SET_NULL, null=True, blank=True,
                             related_name='llm_logs', verbose_name='关联任务')
    learner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                related_name='+', verbose_name='关联学生')
    created_at = models.DateTimeField('调用时间', auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = '大模型调用日志'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']
