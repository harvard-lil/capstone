import Vue from 'vue'
import App from './app'

Vue.config.devtools = true;
Vue.config.productionTip = false;

new Vue({
    el: '#app',
    template: '<App/>',
    components: {App},
});
