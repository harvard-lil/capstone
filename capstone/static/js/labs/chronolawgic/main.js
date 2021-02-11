import Vue from 'vue'
import Timeline from './timeline'
import store from "./store";

new Vue({
    el: '#app',
    store: store,
    template: '<Timeline/>',
    components: {Timeline}
})
