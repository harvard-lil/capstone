import VueRouter from 'vue-router'
import Main from './main.vue'

const router = new VueRouter({
  routes: [
    { path: '/', component: Main, name: 'search' },
  ]
});

export default router