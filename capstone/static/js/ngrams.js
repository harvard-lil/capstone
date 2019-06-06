import Vue from 'vue'
import VueRouter from 'vue-router'
import Main from './ngrams/main'

Vue.config.devtools = true;
Vue.config.productionTip = false;

Vue.use(VueRouter);
const router = new VueRouter({
  mode: 'history',
  base: '/ngrams/',
  routes: [
    {path: '/', component: Main, name: 'main'},
    {path: '*', redirect: '/'},
  ]
});
new Vue({
  el: '#app',
  components: { Main },
  template: '<Main/>',
  router
});