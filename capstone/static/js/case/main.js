// temp workaround for https://github.com/vitejs/vite/issues/4786
if (import.meta.env.MODE !== 'development') {
  import('vite/modulepreload-polyfill')  // https://vitejs.dev/config/#build-polyfillmodulepreload
}

import Vue from 'vue'
import Sidebar from './sidebar.vue'

new Vue({
  el: '#sidebar-menu-content',
  components: { Sidebar },
});