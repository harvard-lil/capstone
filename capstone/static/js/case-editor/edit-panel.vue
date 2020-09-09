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
    },
  }
</script>
