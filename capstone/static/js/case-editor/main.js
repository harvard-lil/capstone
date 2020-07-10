import Vue from 'vue'
import Main from './main.vue'


Vue.config.devtools = true;
Vue.config.productionTip = false;

new Vue({
  el: '#app',
  components: { Main },
  template: '<Main/>'
});



