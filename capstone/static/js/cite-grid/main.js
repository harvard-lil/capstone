// temp workaround for https://github.com/vitejs/vite/issues/4786
if (import.meta.env.MODE !== 'development') {
  import('vite/modulepreload-polyfill')  // https://vitejs.dev/config/#build-polyfillmodulepreload
}

import Vue from 'vue'
import VueRouter from 'vue-router'
import Main from './main.vue'

Vue.config.devtools = true;
Vue.config.productionTip = false;

Vue.use(VueRouter);
const router = new VueRouter({
  mode: 'history',
  base: '/exhibits/cite-grid/',
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