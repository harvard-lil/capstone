import Vue from 'vue'
import Main from './main.vue'


Vue.config.devtools = false;
Vue.config.productionTip = false;

new Vue({
  el: '#app',
  components: { Main },
  template: '<Main/>'
});



