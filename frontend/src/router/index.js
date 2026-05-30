import { createRouter, createWebHistory } from 'vue-router'

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
      path: '/login',
      name: 'login',
      component: () => import('@/views/LoginView.vue'),
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
      path: '/users/:id',
      name: 'user-profile',
      component: () => import('@/views/ProfileView.vue'),
    },
  ],
})

router.beforeEach((to) => {
  const token = localStorage.getItem('access_token')
  if (token && (to.name === 'login' || to.name === 'register')) {
    return { name: 'home' }
  }
})

export default router
