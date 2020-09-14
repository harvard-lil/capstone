<template>
  <div>
    <h4 class="section-title">current word</h4>
    <div :style="currentWordStyle()"></div>
    <div class="row">
      <div class="col-10">
        <input type="text"
               id="current_word"
               :value="currentWord ? currentWord.string : ''"
               placeholder="current word"
               @keydown.tab.exact.prevent="shiftWord(1)"
               @keydown.shift.tab.prevent="shiftWord(-1)"
               @input="$store.commit('editWord', {word: currentWord, string: $event.target.value})">
      </div>
      <div class="col-2"><button @click="addSoftHyphen()" :disabled="currentWord === null">⧟</button></div>
    </div>
  </div>
</template>

<script>
  import { mapState } from 'vuex'
  import {FAKE_SOFT_HYPHEN} from "./helpers";

  export default {
    computed: mapState(['currentWord']),
    methods: {
      currentWordStyle() {
        const word = this.currentWord;
        if (word) {
          const padding=10;  // extra pixels around word
          return {
            'background-image':`url(${word.page.image_url})`,
            'background-size': `${word.page.width}px`,
            width: `${word.w+padding*2}px`,
            height: `${word.h+padding*2}px`,
            'background-position': `-${word.x-padding}px -${word.y-padding}px`,
          };
        } else {
          return {width: '20rem', height: '2rem'};
        }
      },
      addSoftHyphen() {
        this.currentWord.string = this.currentWord.string + FAKE_SOFT_HYPHEN
      },
      shiftWord(offset) {
        /* select next or previous word relative to current word */
        // Order is a tricky concept -- do we mean the next logical word in the case text, next on the page, etc.?
        // We try to select the next word in the case text on the left first, but if the word doesn't appear there,
        // fall back to the next word in the image OCR on the right:
        let currentWordEl =
            document.querySelector(`#caseTextPanel .word-id-${this.currentWord.id}`) ||
            document.querySelector(`#caseImagePanel .word-id-${this.currentWord.id}`);
        // It's also tricky to find the logically-adjacent span.word across paragraphs, footnotes, etc.
        // Find all spans in the same panel as the target word, find the index of the current word,
        // and apply offset:
        const wordEls = Array.from(currentWordEl.closest('.casePanel').querySelectorAll('.word'));
        const index = wordEls.findIndex((el) => el === currentWordEl);
        const newIndex = index + offset;
        if (newIndex < 0 || newIndex > wordEls.length-1)
          return;
        // update current word:
        this.$store.commit('setCurrentWord', this.$store.state.words[wordEls[newIndex].dataset.id]);
      },
    },
  }
</script>
