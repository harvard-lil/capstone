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