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
    contest_rating = models.IntegerField('比赛Rating', default=1500)  # CF 式，仅比赛结算更新
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
    problem_type = models.CharField('题目类型', max_length=10,
                                    choices=[('standard', '标准'), ('function', '函数题')],
                                    default='standard')
    # 函数题模板：{语言: {"template": 给学生的函数签名, "prefix": 隐藏前缀, "suffix": 隐藏驱动main}}
    function_templates = models.JSONField('函数题模板', default=dict, blank=True)
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

    def wrap_code(self, language, code):
        """函数题：用隐藏 prefix/suffix 包裹学生函数体，拼成完整程序交给现有评测。
        非函数题或该语言无模板时返回 None。"""
        if self.problem_type != 'function':
            return None
        cfg = (self.function_templates or {}).get(language)
        if not cfg:
            return None
        return f"{cfg.get('prefix', '')}\n{code}\n{cfg.get('suffix', '')}"


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
        ('NT', '无测试点'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='提交者', related_name='submissions')
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE, verbose_name='题目', related_name='submissions')
    language = models.CharField('编程语言', max_length=10, choices=LANGUAGE_CHOICES, default='C++')
    code = models.TextField('源代码')
    raw_code = models.TextField('学生原始代码', blank=True, default='')  # 函数题：学生填写的函数体；标准题为空
    status = models.CharField('评测结果', max_length=10, choices=STATUS_CHOICES, default='Pending', db_index=True)
    time_used = models.IntegerField('耗时(ms)', null=True, blank=True)
    memory_used = models.IntegerField('内存(KB)', null=True, blank=True)
    error_info = models.TextField('错误信息', blank=True, default='')
    contest = models.ForeignKey('Contest', on_delete=models.SET_NULL, null=True, blank=True, verbose_name='所属比赛', related_name='submissions')
    assignment = models.ForeignKey('Assignment', on_delete=models.SET_NULL, null=True, blank=True, verbose_name='所属作业/考试', related_name='code_submissions')
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
            models.Index(fields=['assignment', 'user']),
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
    team = models.ForeignKey('Team', on_delete=models.SET_NULL, null=True, blank=True, related_name='contests', verbose_name='所属团队')
    rating_applied = models.BooleanField('已结算Rating', default=False)
    freeze_minutes = models.IntegerField('封榜时长（分钟，0=不封榜）', default=0)
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
    points = models.IntegerField('分值（IOI 赛制用）', default=100)
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

class Department(models.Model):
    """院系（组织层级：院系 > 班级/团队），供全校规模分组管理。"""
    name = models.CharField('院系名称', max_length=100, unique=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        db_table = 'judge_department'
        verbose_name = '院系'
        verbose_name_plural = '院系'
        ordering = ['name']

    def __str__(self):
        return self.name


class Team(models.Model):
    """团队/班级，由教师创建"""
    name = models.CharField('团队名称', max_length=100)
    description = models.TextField('简介', blank=True, default='')
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='teams', verbose_name='所属院系')
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
        ('assistant', '助教'),
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
    """团队作业 / 考试容器：练习·作业·考试三态（参照 PTA 题目集）。
    可同时包含编程题（AssignmentProblem）与客观题（AssignmentQuestion）。
    """
    CATEGORY_CHOICES = [
        ('practice', '练习'),
        ('homework', '作业'),
        ('exam', '考试'),
    ]
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='assignments', verbose_name='团队')
    title = models.CharField('作业名称', max_length=200)
    description = models.TextField('作业说明', blank=True, default='')
    category = models.CharField('类型', max_length=10, choices=CATEGORY_CHOICES, default='homework', db_index=True)
    deadline = models.DateTimeField('截止时间', null=True, blank=True)
    # 考试模式专用：绝对时间窗口 + 个人限时 + 防作弊行为
    start_time = models.DateTimeField('开始时间', null=True, blank=True)
    end_time = models.DateTimeField('结束时间', null=True, blank=True)
    duration_minutes = models.IntegerField('个人限时（分钟，0=用整个窗口）', default=0)
    shuffle = models.BooleanField('打乱题序/选项', default=False)
    track_focus = models.BooleanField('记录切屏次数', default=False)
    hide_rank = models.BooleanField('考试中隐藏排名/他人作答', default=False)
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
    score = models.IntegerField('分值', default=10)
    sort_order = models.IntegerField('排序', default=0)

    class Meta:
        db_table = 'judge_assignmentproblem'
        verbose_name = '作业题目'
        verbose_name_plural = '作业题目'
        unique_together = ['assignment', 'problem']
        ordering = ['sort_order', 'id']

    def __str__(self):
        return f'{self.assignment.title} - #{self.problem_id}'


class AssignmentQuestion(models.Model):
    """作业/考试中的客观题（引用题库 Question）"""
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name='question_items', verbose_name='作业')
    question = models.ForeignKey('Question', on_delete=models.CASCADE, related_name='assignment_entries', verbose_name='客观题')
    score = models.IntegerField('分值', default=5)
    sort_order = models.IntegerField('排序', default=0)

    class Meta:
        db_table = 'judge_assignmentquestion'
        verbose_name = '作业客观题'
        verbose_name_plural = '作业客观题'
        unique_together = ['assignment', 'question']
        ordering = ['sort_order', 'id']

    def __str__(self):
        return f'{self.assignment.title} - Q#{self.question_id}'


# ==================== 每日打卡 ====================

class DailyCheckIn(models.Model):
    """用户每日打卡记录，每人每天只能打一次"""
    user    = models.ForeignKey(User, on_delete=models.CASCADE, related_name='checkins', verbose_name='用户')
    date    = models.DateField('打卡日期')
    fortune = models.JSONField('今日运势')  # {"mood": "大吉", "lucky": ["刷题","早睡"], "unlucky": ["摸鱼","熬夜"]}

    class Meta:
        db_table = 'judge_dailycheckin'
        verbose_name = '每日打卡'
        verbose_name_plural = '每日打卡'
        unique_together = ('user', 'date')
        ordering = ['-date']

    def __str__(self):
        return f'{self.user.username} {self.date} {self.fortune.get("mood", "")}'


# ==================== 客观题题库（考试 / 作业用）====================

class Question(models.Model):
    """客观题题库：单选 / 多选 / 判断 / 填空。
    编程题仍用 Problem；本表用于作业与考试的非编程部分，支持自动判分。
    """
    TYPE_CHOICES = [
        ('single', '单选题'),
        ('multiple', '多选题'),
        ('judge', '判断题'),
        ('fill', '填空题'),
    ]

    qtype = models.CharField('题型', max_length=10, choices=TYPE_CHOICES, db_index=True)
    title = models.CharField('题干', max_length=300)
    content = models.TextField('题目详情（Markdown）', blank=True, default='')
    # 选项，仅单选 / 多选使用：[{"key": "A", "text": "..."}, ...]
    options = models.JSONField('选项', default=list, blank=True)
    # 标准答案：
    #   single   -> ["A"]
    #   multiple -> ["A", "C"]
    #   judge    -> ["T"] 或 ["F"]
    #   fill     -> [["空1答案", "空1可接受写法"], ["空2答案"]]  每空一组可接受答案
    answer = models.JSONField('标准答案', default=list)
    blank_ignore_case = models.BooleanField('填空判定忽略大小写', default=True)
    explanation = models.TextField('答案解析（Markdown）', blank=True, default='')
    difficulty = models.CharField('难度', max_length=20,
                                  choices=Problem.DIFFICULTY_CHOICES, default='暂无评定')
    score = models.IntegerField('默认分值', default=5)
    tags = models.ManyToManyField(Tag, blank=True, related_name='questions', verbose_name='标签')
    source = models.CharField('来源', max_length=200, blank=True, default='')
    is_published = models.BooleanField('是否公开', default=False)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                   related_name='created_questions', verbose_name='出题人')
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'judge_question'
        verbose_name = '客观题'
        verbose_name_plural = '客观题'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['qtype']),
            models.Index(fields=['is_published']),
        ]

    def __str__(self):
        return f'[{self.get_qtype_display()}] {self.title[:30]}'

    def check_answer(self, submitted):
        """判定作答是否正确，返回 bool。submitted 格式：
           single / judge -> "A" 或 ["A"]
           multiple       -> ["A", "C"]
           fill           -> ["用户第1空", "用户第2空", ...]
        """
        if self.qtype in ('single', 'multiple', 'judge'):
            sub = submitted if isinstance(submitted, list) else [submitted]
            sub_set = {str(x).strip().upper() for x in sub if str(x).strip() != ''}
            ans_set = {str(x).strip().upper() for x in self.answer}
            return bool(ans_set) and sub_set == ans_set

        if self.qtype == 'fill':
            sub = submitted if isinstance(submitted, list) else [submitted]
            if not self.answer or len(sub) < len(self.answer):
                return False
            for i, accepted in enumerate(self.answer):
                variants = accepted if isinstance(accepted, list) else [accepted]
                user_ans = str(sub[i]).strip()
                if self.blank_ignore_case:
                    user_ans = user_ans.lower()
                    variants = [str(v).strip().lower() for v in variants]
                else:
                    variants = [str(v).strip() for v in variants]
                if user_ans not in variants:
                    return False
            return True

        return False


# ==================== 考试会话与客观题作答 ====================

class ExamParticipation(models.Model):
    """学生进入某作业/考试的会话，用于个人限时与切屏统计。"""
    STATUS_CHOICES = [
        ('in_progress', '进行中'),
        ('submitted', '已交卷'),
        ('graded', '已批改'),
    ]
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name='participations', verbose_name='作业/考试')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='exam_participations', verbose_name='学生')
    started_at = models.DateTimeField('开始时间', auto_now_add=True)
    submitted_at = models.DateTimeField('交卷时间', null=True, blank=True)
    focus_loss_count = models.IntegerField('切屏次数', default=0)
    status = models.CharField('状态', max_length=12, choices=STATUS_CHOICES, default='in_progress')
    total_score = models.IntegerField('总得分', default=0)

    class Meta:
        db_table = 'judge_examparticipation'
        verbose_name = '考试会话'
        verbose_name_plural = '考试会话'
        unique_together = ('assignment', 'user')
        ordering = ['-started_at']

    def __str__(self):
        return f'{self.user.username} @ {self.assignment.title} [{self.status}]'


class QuestionAnswer(models.Model):
    """学生在某作业/考试中对某客观题的作答与自动判分结果。"""
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name='question_answers', verbose_name='作业/考试')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='question_answers', verbose_name='学生')
    question = models.ForeignKey('Question', on_delete=models.CASCADE, related_name='answers', verbose_name='客观题')
    answer = models.JSONField('作答', default=list, blank=True)
    is_correct = models.BooleanField('是否正确', default=False)
    score = models.IntegerField('得分', default=0)
    answered_at = models.DateTimeField('作答时间', auto_now=True)

    class Meta:
        db_table = 'judge_questionanswer'
        verbose_name = '客观题作答'
        verbose_name_plural = '客观题作答'
        unique_together = ('assignment', 'user', 'question')

    def __str__(self):
        return f'{self.user.username} → Q#{self.question_id} ({self.score})'


# ==================== 题单 / 训练计划 ====================

class ProblemList(models.Model):
    """题单：用户自建的有序题目集合，可公开/私有，可挂到团队作为训练计划。"""
    title = models.CharField('标题', max_length=200)
    description = models.TextField('简介', blank=True, default='')
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='problem_lists', verbose_name='创建者')
    team = models.ForeignKey('Team', on_delete=models.CASCADE, null=True, blank=True,
                             related_name='problem_lists', verbose_name='所属团队')
    is_public = models.BooleanField('是否公开', default=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'judge_problemlist'
        verbose_name = '题单'
        verbose_name_plural = '题单'
        ordering = ['-updated_at']

    def __str__(self):
        return self.title


class ProblemListItem(models.Model):
    """题单中的题目"""
    problem_list = models.ForeignKey(ProblemList, on_delete=models.CASCADE, related_name='items', verbose_name='题单')
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE, related_name='list_entries', verbose_name='题目')
    note = models.CharField('备注', max_length=200, blank=True, default='')
    sort_order = models.IntegerField('排序', default=0)

    class Meta:
        db_table = 'judge_problemlistitem'
        verbose_name = '题单题目'
        verbose_name_plural = '题单题目'
        unique_together = ['problem_list', 'problem']
        ordering = ['sort_order', 'id']

    def __str__(self):
        return f'{self.problem_list.title} - #{self.problem_id}'


# ==================== 题解 / 每日一题 ====================

class Solution(models.Model):
    """题解：仅对已 AC 该题的用户可见（防剧透）。"""
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE, related_name='solutions', verbose_name='题目')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='solutions', verbose_name='作者')
    title = models.CharField('标题', max_length=200, blank=True, default='')
    content = models.TextField('题解内容（Markdown）')
    language = models.CharField('语言', max_length=10, blank=True, default='')
    upvotes = models.IntegerField('点赞数', default=0)
    created_at = models.DateTimeField('发布时间', auto_now_add=True)

    class Meta:
        db_table = 'judge_solution'
        verbose_name = '题解'
        verbose_name_plural = '题解'
        ordering = ['-upvotes', '-created_at']
        indexes = [models.Index(fields=['problem', '-upvotes'])]

    def __str__(self):
        return f'{self.user.username} 的题解 @ #{self.problem_id}'


class DailyProblem(models.Model):
    """每日一题：每天一道，可由管理员指定，未指定时按日期确定性自动挑选。"""
    date = models.DateField('日期', unique=True)
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE, related_name='daily_features', verbose_name='题目')
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        db_table = 'judge_dailyproblem'
        verbose_name = '每日一题'
        verbose_name_plural = '每日一题'
        ordering = ['-date']

    def __str__(self):
        return f'{self.date} → #{self.problem_id}'


class RatingChange(models.Model):
    """一场比赛对某用户 contest_rating 的影响，用于画 Rating 曲线。"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='rating_changes', verbose_name='用户')
    contest = models.ForeignKey(Contest, on_delete=models.CASCADE, related_name='rating_changes', verbose_name='比赛')
    rank = models.IntegerField('名次')
    old_rating = models.IntegerField('赛前')
    new_rating = models.IntegerField('赛后')
    delta = models.IntegerField('变化')
    created_at = models.DateTimeField('结算时间', auto_now_add=True)

    class Meta:
        db_table = 'judge_ratingchange'
        verbose_name = 'Rating 变化'
        verbose_name_plural = 'Rating 变化'
        unique_together = ('user', 'contest')
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.username} @ {self.contest_id}: {self.old_rating}→{self.new_rating}'


class VirtualParticipation(models.Model):
    """虚拟参赛：比赛结束后以个人计时重打该场比赛。"""
    contest = models.ForeignKey(Contest, on_delete=models.CASCADE, related_name='virtual_participations', verbose_name='比赛')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='virtual_participations', verbose_name='用户')
    started_at = models.DateTimeField('开始时间', auto_now_add=True)

    class Meta:
        db_table = 'judge_virtualparticipation'
        verbose_name = '虚拟参赛'
        verbose_name_plural = '虚拟参赛'
        unique_together = ('contest', 'user')

    def __str__(self):
        return f'{self.user.username} 虚拟参赛 @ {self.contest_id}'
