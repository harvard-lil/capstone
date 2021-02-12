import Vue from 'vue'
import VueRouter from "vue-router";
import Timeline from './timeline'
import Admin from './admin'
import store from "./store";


Vue.config.devtools = true;
Vue.config.productionTip = false;

Vue.use(VueRouter);
const router = new VueRouter({
  routes: [
    { path: '/', component: Admin, name: 'admin'},
    { path: '/:timeline', component: Timeline, name: 'timeline' },
    { path: '*', redirect: '/' },
  ]
});

new Vue({
    el: '#app',
    store: store,
    template: '<Timeline/>',
    components: {Timeline},
    router
})

