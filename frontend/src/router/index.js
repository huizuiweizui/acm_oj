import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/stores/user'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: () => import('@/views/HomeView.vue'),
    },
    {
      path: '/problems',
      name: 'problem-list',
      component: () => import('@/views/ProblemListView.vue'),
    },
    {
      path: '/problems/:id',
      name: 'problem-detail',
      component: () => import('@/views/ProblemDetailView.vue'),
    },
    {
      path: '/problem-lists',
      name: 'problem-lists',
      component: () => import('@/views/ProblemListsView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/problem-lists/:id',
      name: 'problem-list-detail',
      component: () => import('@/views/ProblemListDetailView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/LoginView.vue'),
      meta: { portal: 'student' },
    },
    {
      path: '/teacher/login',
      name: 'teacher-login',
      component: () => import('@/views/LoginView.vue'),
      meta: { portal: 'teacher' },
    },
    {
      path: '/admin/login',
      name: 'admin-login',
      component: () => import('@/views/LoginView.vue'),
      meta: { portal: 'admin' },
    },
    {
      path: '/register',
      name: 'register',
      component: () => import('@/views/RegisterView.vue'),
    },
    {
      path: '/contests',
      name: 'contest-list',
      component: () => import('@/views/ContestListView.vue'),
    },
    {
      path: '/contests/create',
      name: 'contest-create',
      component: () => import('@/views/ContestCreateView.vue'),
      meta: { requiresAuth: true, requiresContestCreate: true },
    },
    {
      path: '/contests/:id',
      name: 'contest-detail',
      component: () => import('@/views/ContestDetailView.vue'),
    },
    {
      path: '/contests/:id/rank',
      name: 'contest-rank',
      component: () => import('@/views/ContestRankingView.vue'),
    },
    {
      path: '/submissions',
      name: 'submissions',
      component: () => import('@/views/SubmissionsView.vue'),
    },
    {
      path: '/rank',
      name: 'rank',
      component: () => import('@/views/LeaderboardView.vue'),
    },
    {
      path: '/discussions',
      name: 'discussion-list',
      component: () => import('@/views/DiscussionListView.vue'),
    },
    {
      path: '/discussions/create',
      name: 'discussion-create',
      component: () => import('@/views/DiscussionCreateView.vue'),
    },
    {
      path: '/discussions/:id',
      name: 'discussion-detail',
      component: () => import('@/views/DiscussionDetailView.vue'),
    },
    {
      path: '/learn',
      name: 'learn',
      component: () => import('@/views/LearnView.vue'),
    },
    {
      path: '/learn/graph',
      name: 'learn-graph',
      component: () => import('@/views/LearnGraphView.vue'),
    },
    {
      path: '/learn/:id',
      name: 'learn-detail',
      component: () => import('@/views/LearnDetailView.vue'),
    },
    {
      path: '/users/:id',
      name: 'user-profile',
      component: () => import('@/views/ProfileView.vue'),
    },

    // ==================== 学生端 ====================
    {
      path: '/my-teams',
      name: 'my-teams',
      component: () => import('@/views/student/MyTeamsView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/my-teams/:id',
      name: 'student-team',
      component: () => import('@/views/student/StudentTeamView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/exam/:aid',
      name: 'exam',
      component: () => import('@/views/student/ExamView.vue'),
      meta: { requiresAuth: true },
    },

    // ==================== 教师端 ====================
    {
      path: '/teacher',
      name: 'teacher-dashboard',
      component: () => import('@/views/teacher/DashboardView.vue'),
      meta: { requiresAuth: true, requiresRole: 'teacher' },
    },
    {
      path: '/teacher/questions',
      name: 'teacher-questions',
      component: () => import('@/views/teacher/QuestionBankView.vue'),
      meta: { requiresAuth: true, requiresRole: 'teacher' },
    },
    {
      path: '/teacher/assignments/:aid/gradebook',
      name: 'teacher-gradebook',
      component: () => import('@/views/teacher/GradebookView.vue'),
      meta: { requiresAuth: true },   // 后端 _is_manager 控制权限
    },
    {
      path: '/teacher/assignments/:aid/plagiarism',
      name: 'teacher-plagiarism',
      component: () => import('@/views/teacher/PlagiarismView.vue'),
      meta: { requiresAuth: true },   // 后端 _is_manager 控制权限
    },
    {
      path: '/teacher/teams/:id',
      name: 'teacher-team-detail',
      component: () => import('@/views/teacher/TeamDetailView.vue'),
      meta: { requiresAuth: true },   // 后端 _is_team_viewer 控制权限（教师+队长）
    },
    {
      path: '/teacher/teams/:id/dashboard',
      name: 'teacher-team-dashboard',
      component: () => import('@/views/teacher/TeamDashboardView.vue'),
      meta: { requiresAuth: true },   // 后端控制权限
    },
    {
      path: '/teacher/teams/:teamId/students/:userId',
      name: 'teacher-student-detail',
      component: () => import('@/views/teacher/StudentDetailView.vue'),
      meta: { requiresAuth: true },   // 后端控制权限
    },

    // ==================== 管理员端 ====================
    {
      path: '/admin',
      name: 'admin-dashboard',
      component: () => import('@/views/admin/DashboardView.vue'),
      meta: { requiresAuth: true, requiresRole: 'admin' },
    },
    {
      path: '/admin/users',
      name: 'admin-users',
      component: () => import('@/views/admin/UserManageView.vue'),
      meta: { requiresAuth: true, requiresRole: 'admin' },
    },

    // ==================== 修改密码 ====================
    {
      path: '/change-password',
      name: 'change-password',
      component: () => import('@/views/ChangePasswordView.vue'),
      meta: { requiresAuth: true },
    },

    // ==================== 错误页 ====================
    {
      path: '/403',
      name: 'forbidden',
      component: () => import('@/views/ForbiddenView.vue'),
    },
  ],
})

// 根据 requiresRole 决定跳转哪个登录页
function loginRouteFor(to) {
  const role = to.meta.requiresRole
  if (role === 'admin') return { name: 'admin-login', query: { next: to.fullPath } }
  if (role === 'teacher') return { name: 'teacher-login', query: { next: to.fullPath } }
  return { name: 'login', query: { next: to.fullPath } }
}

router.beforeEach(async (to) => {
  const userStore = useUserStore()

  // fetchMe 前先读一次 token
  const tokenBefore = localStorage.getItem('access_token')

  // token 存在但用户数据尚未加载（页面刷新场景）——先取回用户信息再做角色判断
  // fetchMe 失败时会调用 logout() 清除 localStorage，所以之后必须重读 token
  if (tokenBefore && !userStore.user) {
    await userStore.fetchMe()
  }

  // fetchMe 可能调用了 logout()，重新读取最新 token
  const token = localStorage.getItem('access_token')

  // 已登录用户不再访问登录/注册页
  if (token && (to.name === 'login' || to.name === 'teacher-login' || to.name === 'admin-login' || to.name === 'register')) {
    return { name: 'home' }
  }

  // 需要登录的页面
  if (to.meta.requiresAuth && !token) {
    return loginRouteFor(to)
  }

  // 已登录时：若 must_change_password，除修改密码页外全部拦截
  if (token && to.name !== 'change-password') {
    if (userStore.user?.must_change_password) {
      return { name: 'change-password' }
    }
  }

  // 需要创建比赛权限
  if (to.meta.requiresContestCreate) {
    const role = userStore.user?.role
    const hasPerm = ['teacher', 'admin'].includes(role) || !!userStore.user?.can_create_contest
    if (!hasPerm) {
      return { name: 'forbidden' }
    }
  }

  // 需要特定角色
  if (to.meta.requiresRole) {
    const role = userStore.user?.role
    const required = to.meta.requiresRole

    // admin 可以访问 teacher 路由；其他角色必须精确匹配
    const allowed = required === 'teacher'
      ? ['teacher', 'admin'].includes(role)
      : role === required

    if (!allowed) {
      return { name: 'forbidden' }
    }
  }
})

export default router
