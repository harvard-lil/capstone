import Vue from 'vue'
import Vuex from 'vuex'
import { BootstrapVue } from 'bootstrap-vue'
import 'bootstrap-vue/dist/bootstrap-vue.css'
import scrollIntoView from 'scroll-into-view-if-needed';
import { getField, updateField } from 'vuex-map-fields';

import Main from './main.vue'

Vue.use(Vuex)
Vue.use(BootstrapVue)

function wordElements(word) {
  return document.querySelectorAll(`.word-id-${word.id}`);
}

function forWordElements(word, f) {
  /* helper to manually apply DOM updates to words, for speed on large cases */
  for (const el of wordElements(word))
    f(el);
}

const store = new Vuex.Store({
  state: {
    words: {},
    metadata: {},
    currentWord: null,
    editedWords: {},
    showConfidence: false,
    showOcr: false,
  },
  getters: {
    getField,  // for v-model binding
  },
  mutations: {
    updateField,  // for v-model binding
    setMetadata(state, metadata) {
      state.metadata = metadata;
    },
    addWord(state, word) {
      Vue.set(state.words, word.id, word);
    },
    setCurrentWord (state, word) {
      if (state.currentWord === word)
        return;
      if (state.currentWord !== null) {
        Vue.set(state.currentWord, 'isCurrent', false);
        forWordElements(state.currentWord, (el) => el.classList.remove('current-word'));
      }
      Vue.set(word, 'isCurrent', true);
      forWordElements(word, (el) => el.classList.add('current-word'));
      state.currentWord = word;

      // focus and scroll
      document.getElementById('current_word').focus();
      requestAnimationFrame(()=> forWordElements(word, (el) => scrollIntoView(el, {scrollMode: 'if-needed'})));
    },
    editWord(state, {word, string}) {
      if (word.originalString === string) {
        Vue.delete(state.editedWords, word.id);
        forWordElements(word, (el) => el.classList.remove('edited'));
      } else {
        Vue.set(state.editedWords, word.id, word);
        forWordElements(word, (el) => el.classList.add('edited'));
      }
      Vue.set(word, 'string', string);
      forWordElements(word, (el) => el.innerText = string);
    },
    removeEdit(state, word) {
      this.commit("editWord", {word, string: word.originalString});
    },
    toggleConfidence(state) {
      state.showConfidence = !state.showConfidence;
    },
    toggleOcr(state) {
      state.showOcr = !state.showOcr;
    },
  }
});

new Vue({
  el: '#app',
  components: { Main },
  template: '<Main/>',
  store: store,
});



