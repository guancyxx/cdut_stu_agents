// Router configuration — independent routes for each OJ section.
import { createRouter, createWebHistory } from 'vue-router'

import AuthPage from '../pages/AuthPage.vue'
import HomePage from '../pages/HomePage.vue'
import ProblemsetPage from '../pages/ProblemsetPage.vue'
import ContestPage from '../pages/ContestPage.vue'
import AdminPage from '../pages/AdminPage.vue'
import ProfilePage from '../pages/ProfilePage.vue'

const routes = [
  {
    path: '/',
    name: 'home',
    component: HomePage,
    meta: { title: '主页' }
  },
  {
    path: '/problemset',
    name: 'problemset',
    component: ProblemsetPage,
    meta: { title: '题库' }
  },
  {
    path: '/contest',
    name: 'contest',
    component: ContestPage,
    meta: { title: '比赛' }
  },
  {
    path: '/admin',
    name: 'admin',
    component: AdminPage,
    meta: { title: '管理' }
  },
  {
    path: '/profile',
    name: 'profile',
    component: ProfilePage,
    meta: { title: '个人中心' }
  },
  {
    path: '/auth',
    name: 'auth',
    component: AuthPage,
    meta: { title: '登录 / 注册' }
  },
  {
    // Catch-all: redirect to home
    path: '/:pathMatch(.*)*',
    redirect: '/'
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
