import Vue from 'vue'
import VueRouter from 'vue-router'
import Main from './main.vue'

Vue.config.devtools = true;
Vue.config.productionTip = false;

Vue.use(VueRouter);
const router = new VueRouter({
  routes: [
    { path: '/:endpoint', component: Main, name: 'endpoint' },
    { path: '/', redirect: '/cases' },
    { path: '*', redirect: '/' },
  ]
});
new Vue({
  el: '#app',
  components: { Main },
  template: '<Main/>',
  router
});