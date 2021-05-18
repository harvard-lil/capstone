import Vue from 'vue'
import VueRouter from "vue-router";
import Timeline from './timeline'
import Admin from './admin'
import App from './app'
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
