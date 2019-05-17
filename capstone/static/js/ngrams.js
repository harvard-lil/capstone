import Vue from 'vue'
import Main from './ngrams/main'

Vue.config.devtools = true;
Vue.config.productionTip = false;

new Vue({
  el: '#app',
  components: { Main },
  template: '<Main/>',
});