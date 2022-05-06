// temp workaround for https://github.com/vitejs/vite/issues/4786
if (import.meta.env.MODE !== 'development') {
  import('vite/modulepreload-polyfill')  // https://vitejs.dev/config/#build-polyfillmodulepreload
}

import Vue from 'vue'
import Main from './main.vue'
import store from "./store";
import VueRouter from 'vue-router'
import router from "./router";


Vue.config.devtools = true;
Vue.config.productionTip = false;


Vue.use(VueRouter);

new Vue({
  el: '#app',
  components: { Main },
  template: '<Main/>',
  store,
  router
});