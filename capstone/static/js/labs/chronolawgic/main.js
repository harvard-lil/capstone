// temp workaround for https://github.com/vitejs/vite/issues/4786
if (import.meta.env.MODE !== 'development') {
  import('vite/modulepreload-polyfill')  // https://vitejs.dev/config/#build-polyfillmodulepreload
}

import Vue from 'vue'
import VueRouter from "vue-router";
import Timeline from './timeline.vue'
import Admin from './admin.vue'
import App from './app.vue'
import store from "./store";

Vue.config.devtools = true;
Vue.config.productionTip = false;

Vue.use(VueRouter);
export const router = new VueRouter({
    mode: 'history',
    base: 'labs/chronolawgic/timeline/',
    routes: [
        {path: '/', component: Admin, name: 'admin'},
        {path: '/:timeline', component: Timeline, name: 'timeline'},
        {path: '*', redirect: '/'},
    ]
});
router.afterEach((to) => {
    if (to.name === 'timeline' && to.params.timeline) {
        store.dispatch('requestTimeline', to.params.timeline);
    }
    if (to.name === 'admin') {
        store.dispatch('requestTimelineList');
    }
})

new Vue({
    el: '#app',
    store: store,
    template: '<App/>',
    components: {App, Timeline, Admin},
    router
});
