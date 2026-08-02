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
        ('student', '学生'),
        ('teacher', '教师'),
        ('admin', '管理员'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    avatar_url = models.URLField('头像地址', max_length=500, blank=True, default='')
    avatar_color = models.CharField('头像颜色', max_length=7, default='#4F46E5')
    role = models.CharField('角色', max_length=10, choices=ROLE_CHOICES, default='student')
    ac_count = models.IntegerField('AC题目数', default=0)
    submit_count = models.IntegerField('总提交数', default=0)
    rating = models.IntegerField('Rating', default=1500)
    bio = models.CharField('个人简介', max_length=200, blank=True, default='')
    # 学籍字段
    student_id = models.CharField('学号', max_length=30, blank=True, default='', db_index=True)
    real_name = models.CharField('真实姓名', max_length=50, blank=True, default='')
    major = models.CharField('专业', max_length=100, blank=True, default='')
    grade = models.CharField('年级', max_length=20, blank=True, default='')
    must_change_password = models.BooleanField('首次登录需改密', default=False)
    can_create_contest = models.BooleanField('可创建比赛', default=False)
    is_super_admin = models.BooleanField('总管理员', default=False)

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
        ('暂无评定', '暂无评定'),
        ('入门', '入门'),
        ('普及-', '普及-'),
        ('普及/提高-', '普及/提高-'),
        ('普及+/提高', '普及+/提高'),
        ('提高+/省选-', '提高+/省选-'),
        ('省选/NOI-', '省选/NOI-'),
        ('NOI/NOI+/CTSC', 'NOI/NOI+/CTSC'),
    ]

    title = models.CharField('题目标题', max_length=200)
    description = models.TextField('题面描述（Markdown）')
    input_desc = models.TextField('输入格式说明')
    output_desc = models.TextField('输出格式说明')
    sample_input = models.TextField('样例输入')
    sample_output = models.TextField('样例输出')
    hint = models.TextField('提示', blank=True, default='')
    difficulty = models.CharField('难度', max_length=20, choices=DIFFICULTY_CHOICES, default='暂无评定', db_index=True)
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
        submit = getattr(self, 'real_submit_count', None)
        ac = getattr(self, 'real_ac_count', None)
        if submit is None:
            submit = self.submissions.count()
            ac = self.submissions.filter(status='AC').count()
        if not submit:
            return 0
        return round(ac / submit * 100, 1)


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
        ('OLE', 'Output Limit Exceeded'),
        ('RE', 'Runtime Error'),
        ('CE', 'Compilation Error'),
        ('NT', '无测试点'),
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
    test_results = models.JSONField('测试点结果', default=list, blank=True)
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


# ==================== 算法学习 ====================

class Algorithm(models.Model):
    DIFFICULTY_CHOICES = [
        ('入门', '入门'),
        ('提高', '提高'),
        ('进阶', '进阶'),
    ]

    algo_id = models.CharField('算法ID', max_length=50, unique=True)
    name = models.CharField('算法名称', max_length=50)
    name_en = models.CharField('英文名', max_length=100)
    category = models.CharField('分类', max_length=20)
    difficulty = models.CharField('难度', max_length=10, choices=DIFFICULTY_CHOICES)
    desc = models.CharField('卡片描述', max_length=300)
    description = models.TextField('详细简介', blank=True, default='')
    steps = models.JSONField('执行步骤', default=list, blank=True)
    complexity = models.JSONField('时空复杂度', default=list, blank=True)
    stable = models.BooleanField('是否稳定排序', null=True, blank=True)
    codes = models.JSONField('参考代码', default=dict, blank=True)
    sort_order = models.IntegerField('排序', default=0)

    class Meta:
        db_table = 'judge_algorithm'
        verbose_name = '算法知识点'
        verbose_name_plural = '算法知识点'
        ordering = ['sort_order', 'id']

    def __str__(self):
        return f'{self.name} ({self.algo_id})'


class KnowledgeChunk(models.Model):
    """算法笔记按二级标题切分后的片段"""
    source_file = models.CharField('来源文件', max_length=300)
    algo        = models.ForeignKey(Algorithm, null=True, blank=True,
                                    on_delete=models.SET_NULL, related_name='chunks')
    section     = models.CharField('章节标题', max_length=200, blank=True)
    content     = models.TextField('原文内容')
    token_count = models.IntegerField('估算 token 数', default=0)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'judge_knowledgechunk'
        verbose_name = '知识片段'
        verbose_name_plural = '知识片段'

    def __str__(self):
        return f'{self.source_file} § {self.section}'


class ChunkEmbedding(models.Model):
    """知识片段对应的向量（单独存，避免 chunk 表过重）"""
    chunk      = models.OneToOneField(KnowledgeChunk, on_delete=models.CASCADE,
                                       related_name='embedding')
    vector     = models.JSONField('向量')          # list[float]
    model_name = models.CharField('Embedding 模型', max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'judge_chunkembedding'
        verbose_name = 'Chunk 向量'
        verbose_name_plural = 'Chunk 向量'


class AlgorithmEdge(models.Model):
    EDGE_TYPES = [
        ('prerequisite', '前置依赖'),
        ('related',      '相关算法'),
        ('extends',      '扩展应用'),
    ]
    source = models.ForeignKey(Algorithm, related_name='out_edges', on_delete=models.CASCADE)
    target = models.ForeignKey(Algorithm, related_name='in_edges',  on_delete=models.CASCADE)
    edge_type = models.CharField(max_length=20, choices=EDGE_TYPES, default='related')

    class Meta:
        db_table = 'judge_algorithmedge'
        verbose_name = '算法关系边'
        verbose_name_plural = '算法关系边'
        unique_together = ['source', 'target']

    def __str__(self):
        return f'{self.source.algo_id} --{self.edge_type}--> {self.target.algo_id}'


# ==================== 团队（班级）====================

class Team(models.Model):
    """团队/班级，由教师创建"""
    name = models.CharField('团队名称', max_length=100)
    description = models.TextField('简介', blank=True, default='')
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_teams', verbose_name='创建教师')
    invite_code = models.CharField('邀请码', max_length=8, unique=True)
    need_review = models.BooleanField('加入需审核', default=True)
    is_active = models.BooleanField('是否启用', default=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        db_table = 'judge_team'
        verbose_name = '团队'
        verbose_name_plural = '团队'
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class TeamMembership(models.Model):
    """团队成员"""
    ROLE_CHOICES = [
        ('captain', '队长'),
        ('member', '队员'),
    ]
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='memberships', verbose_name='团队')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='team_memberships', verbose_name='用户')
    role = models.CharField('成员角色', max_length=10, choices=ROLE_CHOICES, default='member')
    remark = models.CharField('团队内备注', max_length=50, blank=True, default='')
    joined_at = models.DateTimeField('加入时间', auto_now_add=True)

    class Meta:
        db_table = 'judge_teammembership'
        verbose_name = '团队成员'
        verbose_name_plural = '团队成员'
        unique_together = ('team', 'user')

    def __str__(self):
        return f'{self.user.username} @ {self.team.name}'

    @property
    def display_name(self):
        """备注 > 真实姓名 > 用户名"""
        if self.remark:
            return self.remark
        try:
            real = self.user.profile.real_name
            return real if real else self.user.username
        except Exception:
            return self.user.username


class TeamJoinRequest(models.Model):
    """加入团队申请"""
    STATUS_CHOICES = [
        ('pending', '待审核'),
        ('approved', '已通过'),
        ('rejected', '已拒绝'),
    ]
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='join_requests', verbose_name='团队')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='team_join_requests', verbose_name='申请人')
    remark = models.CharField('申请备注', max_length=100, help_text='请填写如「2023级 张三」，教师将以此识别你的身份')
    status = models.CharField('状态', max_length=10, choices=STATUS_CHOICES, default='pending')
    reject_reason = models.TextField('拒绝理由', blank=True, default='')
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='reviewed_requests', verbose_name='审核人')
    reviewed_at = models.DateTimeField('审核时间', null=True, blank=True)
    created_at = models.DateTimeField('申请时间', auto_now_add=True)

    class Meta:
        db_table = 'judge_teamjoinrequest'
        verbose_name = '加入申请'
        verbose_name_plural = '加入申请'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.username} → {self.team.name} [{self.status}]'


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


# ==================== 作业与公告 ====================

class Announcement(models.Model):
    """团队公告"""
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='announcements', verbose_name='团队')
    title = models.CharField('标题', max_length=200)
    content = models.TextField('内容（Markdown）', blank=True, default='')
    is_pinned = models.BooleanField('置顶', default=False)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_announcements')
    created_at = models.DateTimeField('发布时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'judge_announcement'
        verbose_name = '公告'
        verbose_name_plural = '公告'
        ordering = ['-is_pinned', '-created_at']

    def __str__(self):
        return f'[{self.team.name}] {self.title}'


class Assignment(models.Model):
    """团队作业"""
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='assignments', verbose_name='团队')
    title = models.CharField('作业名称', max_length=200)
    description = models.TextField('作业说明', blank=True, default='')
    deadline = models.DateTimeField('截止时间', null=True, blank=True)
    is_active = models.BooleanField('是否发布', default=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_assignments')
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'judge_assignment'
        verbose_name = '作业'
        verbose_name_plural = '作业'
        ordering = ['-created_at']

    def __str__(self):
        return f'[{self.team.name}] {self.title}'


class AssignmentProblem(models.Model):
    """作业题目"""
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name='problems', verbose_name='作业')
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE, related_name='assignment_entries', verbose_name='题目')
    sort_order = models.IntegerField('排序', default=0)

    class Meta:
        db_table = 'judge_assignmentproblem'
        verbose_name = '作业题目'
        verbose_name_plural = '作业题目'
        unique_together = ['assignment', 'problem']
        ordering = ['sort_order', 'id']

    def __str__(self):
        return f'{self.assignment.title} - #{self.problem_id}'
