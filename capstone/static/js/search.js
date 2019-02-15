import Vue from 'vue'
import Main from './search/main'

Vue.config.devtools = true
Vue.config.productionTip = false

/* eslint-disable no-new */

new Vue({
  el: '#app',
  components: { Main },
  template: '<Main/>',
});