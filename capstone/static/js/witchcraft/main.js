// temp workaround for https://github.com/vitejs/vite/issues/4786
if (import.meta.env.MODE !== 'development') {
  import('vite/modulepreload-polyfill')  // https://vitejs.dev/config/#build-polyfillmodulepreload
}

import Vue from 'vue'
import Main from './main.vue'


new Vue({
  el: '#app',
  components: { Main },
  template: '<Main/>',
});