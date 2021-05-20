import Vue from 'vue'
import Main from './main.vue'
import store from "./store";


Vue.config.devtools = true;
Vue.config.productionTip = false;


new Vue({
  el: '#app',
  components: { Main },
  template: '<Main/>',
  store
});