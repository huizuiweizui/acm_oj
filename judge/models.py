"""
ACM 算法竞赛平台 数据模型
对应技术方案书第三章数据库设计：
users / problems / tags / test_cases / submissions / contests /
contest_problems / contest_participants / discussions / discussion_replies
"""
from django.db import models
from django.contrib.auth.models import User


# ==================== 用户扩展 ====================

class UserProfile(models.Model):
    """用户扩展资料（扩展 Django 内置 User 表）"""
    ROLE_CHOICES = [
        ('user', '普通用户'),
        ('admin', '管理员'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    avatar_url = models.URLField('头像地址', max_length=500, blank=True, default='')
    avatar_color = models.CharField('头像颜色', max_length=7, default='#4F46E5')
    role = models.CharField('角色', max_length=10, choices=ROLE_CHOICES, default='user')
    ac_count = models.IntegerField('AC题目数', default=0)
    submit_count = models.IntegerField('总提交数', default=0)
    rating = models.IntegerField('Rating', default=1500)
    bio = models.CharField('个人简介', max_length=200, blank=True, default='')

    class Meta:
        db_table = 'judge_userprofile'
        verbose_name = '用户资料'
        verbose_name_plural = '用户资料'

    def __str__(self):
        return f'{self.user.username} ({self.get_role_display()})'


# ==================== 题库系统 ====================

class Tag(models.Model):
    """标签（如：DP、图论、贪心、搜索、数据结构、数学、字符串）"""
    name = models.CharField('标签名', max_length=50, unique=True)

    class Meta:
        db_table = 'judge_tag'
        verbose_name = '标签'
        verbose_name_plural = '标签'

    def __str__(self):
        return self.name


class Problem(models.Model):
    """题目"""
    DIFFICULTY_CHOICES = [
        ('Easy', 'Easy'),
        ('Medium', 'Medium'),
        ('Hard', 'Hard'),
    ]

    title = models.CharField('题目标题', max_length=200)
    description = models.TextField('题面描述（Markdown）')
    input_desc = models.TextField('输入格式说明')
    output_desc = models.TextField('输出格式说明')
    sample_input = models.TextField('样例输入')
    sample_output = models.TextField('样例输出')
    hint = models.TextField('提示', blank=True, default='')
    difficulty = models.CharField('难度', max_length=10, choices=DIFFICULTY_CHOICES, default='Medium', db_index=True)
    time_limit = models.IntegerField('时间限制(ms)', default=1000)
    memory_limit = models.IntegerField('内存限制(MB)', default=256)
    ac_count = models.IntegerField('通过人数', default=0)
    submit_count = models.IntegerField('提交次数', default=0)
    source = models.CharField('来源', max_length=200, blank=True, default='')
    is_published = models.BooleanField('是否公开', default=False)
    tags = models.ManyToManyField(Tag, blank=True, verbose_name='标签', related_name='problems')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name='出题人', related_name='created_problems')
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'judge_problem'
        verbose_name = '题目'
        verbose_name_plural = '题目'
        ordering = ['id']
        indexes = [
            models.Index(fields=['difficulty']),
        ]

    def __str__(self):
        return f'#{self.id} {self.title}'

    @property
    def ac_rate(self):
        if self.submit_count == 0:
            return 0
        return round(self.ac_count / self.submit_count * 100, 1)


class TestCase(models.Model):
    """测试数据"""
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE, related_name='test_cases', verbose_name='题目')
    input_data = models.TextField('输入数据')
    expected_output = models.TextField('期望输出')
    is_sample = models.BooleanField('是否样例', default=False)
    sort_order = models.IntegerField('排序', default=0)

    class Meta:
        db_table = 'judge_testcase'
        verbose_name = '测试数据'
        verbose_name_plural = '测试数据'
        ordering = ['sort_order']

    def __str__(self):
        return f'题目#{self.problem_id} 测试点#{self.sort_order}'


# ==================== 提交与评测 ====================

class Submission(models.Model):
    """提交记录"""
    LANGUAGE_CHOICES = [
        ('C', 'C'),
        ('C++', 'C++'),
        ('Java', 'Java'),
        ('Python', 'Python'),
    ]
    STATUS_CHOICES = [
        ('Pending', '等待评测'),
        ('Judging', '评测中'),
        ('AC', 'Accepted'),
        ('WA', 'Wrong Answer'),
        ('TLE', 'Time Limit Exceeded'),
        ('MLE', 'Memory Limit Exceeded'),
        ('RE', 'Runtime Error'),
        ('CE', 'Compilation Error'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='提交者', related_name='submissions')
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE, verbose_name='题目', related_name='submissions')
    language = models.CharField('编程语言', max_length=10, choices=LANGUAGE_CHOICES, default='C++')
    code = models.TextField('源代码')
    status = models.CharField('评测结果', max_length=10, choices=STATUS_CHOICES, default='Pending', db_index=True)
    time_used = models.IntegerField('耗时(ms)', null=True, blank=True)
    memory_used = models.IntegerField('内存(KB)', null=True, blank=True)
    error_info = models.TextField('错误信息', blank=True, default='')
    contest = models.ForeignKey('Contest', on_delete=models.SET_NULL, null=True, blank=True, verbose_name='所属比赛', related_name='submissions')
    ai_feedback = models.TextField('AI评测反馈', blank=True, default='')
    submitted_at = models.DateTimeField('提交时间', auto_now_add=True)

    class Meta:
        db_table = 'judge_submission'
        verbose_name = '提交记录'
        verbose_name_plural = '提交记录'
        ordering = ['-submitted_at']
        indexes = [
            models.Index(fields=['user', 'problem']),
            models.Index(fields=['problem', 'status']),
            models.Index(fields=['contest', 'submitted_at']),
            models.Index(fields=['user', 'submitted_at']),
        ]

    def __str__(self):
        return f'{self.user.username} → #{self.problem_id} [{self.status}]'


# ==================== 比赛系统 ====================

class Contest(models.Model):
    """比赛"""
    RULE_CHOICES = [
        ('ICPC', 'ICPC'),
        ('IOI', 'IOI'),
    ]

    title = models.CharField('比赛名称', max_length=200)
    description = models.TextField('比赛说明', blank=True, default='')
    start_time = models.DateTimeField('开始时间')
    end_time = models.DateTimeField('结束时间')
    rule_type = models.CharField('赛制', max_length=4, choices=RULE_CHOICES, default='ICPC')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name='创建者', related_name='created_contests')
    is_public = models.BooleanField('是否公开', default=True)
    password = models.CharField('私有赛密码', max_length=50, blank=True, default='')
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        db_table = 'judge_contest'
        verbose_name = '比赛'
        verbose_name_plural = '比赛'
        ordering = ['-start_time']

    def __str__(self):
        return self.title

    @property
    def status(self):
        from django.utils import timezone
        now = timezone.now()
        if now < self.start_time:
            return 'upcoming'
        elif now > self.end_time:
            return 'ended'
        return 'running'


class ContestProblem(models.Model):
    """比赛题目"""
    contest = models.ForeignKey(Contest, on_delete=models.CASCADE, related_name='contest_problems')
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE, related_name='contest_entries')
    label = models.CharField('编号（A/B/C...）', max_length=2)
    sort_order = models.IntegerField('排序', default=0)

    class Meta:
        db_table = 'judge_contestproblem'
        verbose_name = '比赛题目'
        verbose_name_plural = '比赛题目'
        unique_together = ['contest', 'problem']
        ordering = ['sort_order']

    def __str__(self):
        return f'{self.contest.title} - {self.label}'


class ContestParticipant(models.Model):
    """比赛参与者"""
    contest = models.ForeignKey(Contest, on_delete=models.CASCADE, related_name='participants')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='contest_participations')
    score = models.IntegerField('总分', default=0)
    penalty = models.IntegerField('罚时（分钟）', default=0)
    registered_at = models.DateTimeField('报名时间', auto_now_add=True)

    class Meta:
        db_table = 'judge_contestparticipant'
        verbose_name = '比赛参与者'
        verbose_name_plural = '比赛参与者'
        unique_together = ['contest', 'user']

    def __str__(self):
        return f'{self.user.username} @ {self.contest.title}'


# ==================== 讨论区 ====================

class Discussion(models.Model):
    """讨论帖"""
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE, null=True, blank=True, verbose_name='关联题目', related_name='discussions')
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='发帖人', related_name='discussions')
    title = models.CharField('帖子标题', max_length=200)
    content = models.TextField('内容（Markdown）')
    view_count = models.IntegerField('浏览量', default=0)
    created_at = models.DateTimeField('发布时间', auto_now_add=True)

    class Meta:
        db_table = 'judge_discussion'
        verbose_name = '讨论帖'
        verbose_name_plural = '讨论帖'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['problem']),
        ]

    def __str__(self):
        return self.title

    @property
    def reply_count(self):
        return self.replies.count()


class DiscussionReply(models.Model):
    """讨论回复"""
    discussion = models.ForeignKey(Discussion, on_delete=models.CASCADE, related_name='replies', verbose_name='所属帖子')
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='回复人', related_name='discussion_replies')
    content = models.TextField('回复内容')
    created_at = models.DateTimeField('回复时间', auto_now_add=True)

    class Meta:
        db_table = 'judge_discussionreply'
        verbose_name = '讨论回复'
        verbose_name_plural = '讨论回复'
        ordering = ['created_at']

    def __str__(self):
        return f'{self.user.username} 回复 {self.discussion.title}'
