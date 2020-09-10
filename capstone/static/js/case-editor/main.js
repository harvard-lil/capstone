import Vue from 'vue'
import Vuex from 'vuex'
import scrollIntoView from 'scroll-into-view-if-needed';
import { getField, updateField } from 'vuex-map-fields';

import Main from './main.vue'

Vue.use(Vuex)

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
      if (state.currentWord !== null)
        Vue.set(state.currentWord, 'isCurrent', false);
      Vue.set(word, 'isCurrent', true);
      state.currentWord = word;

      // focus and scroll
      document.getElementById('current_word').focus();
      for (const el of document.querySelectorAll(`.word-id-${word.id}`)){
        scrollIntoView(el, {scrollMode: 'if-needed'});
      }
    },
    editWord(state, {word, string}) {
      if (word.originalString === string)
        Vue.delete(state.editedWords, word.id);
      else
        Vue.set(state.editedWords, word.id, word);
      Vue.set(word, 'string', string);
    },
    removeEdit(state, word) {
      Vue.set(word, 'string', word.originalString);
      Vue.delete(state.editedWords, word.id);
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



