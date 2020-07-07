import Vue from 'vue'
import Main from './case-editor/main'
import store from "./case-editor/store";



Vue.config.devtools = true;
Vue.config.productionTip = false;

new Vue({
  el: '#app',
  components: { Main },
  store: store,
  beforeCreate() { this.$store.commit('initialise_store');},
  template: '<Main/>'
});



