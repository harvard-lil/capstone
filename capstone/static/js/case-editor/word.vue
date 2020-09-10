<template>
  <span :style="wordStyle()"
        :class="wordClass()"
        @click="$store.commit('setCurrentWord', word)"
  >{{wordString()}}</span>
</template>

<script>
  import { mapState } from 'vuex'
  import {FAKE_SOFT_HYPHEN} from "static/js/case-editor/helpers";

  export default {
    props: ['image', 'wordId', 'page'],
    computed: {
      ...mapState(['showConfidence']),
      word () {
        return this.$store.state.words[this.wordId];
      }
    },
    methods: {
      wordStyle() {
        const word = this.word;
        const font = word.font;
        if (this.image) {
          const page = this.page;
          return {
            left: `${word.x * page.scale}px`,
            top: `${word.y * page.scale - word.yOffset * page.fontScale - 1}px`,  // -1 for top border
            'background-color': this.showConfidence ? word.wordConfidenceColor : 'unset',
            // font format is "<styles> <font size>/<line height> <font families>":
            font: `${font.styles} ${font.size * page.fontScale}px/${word.lineHeight * page.fontScale}px ${font.family}`,
          };
        } else {
          return {
            'background-color': this.showConfidence ? word.wordConfidenceColor : 'unset',
            font: font.styles,
          };
        }
      },
      wordClass() {
        const word = this.word;
        return {
          'edited': word.string !== word.originalString,
          'footnote-mark': word.footnoteMark,
          'current-word': word.isCurrent,
          [`word-id-${word.id}`]: true,
        };
      },
      wordString() {
        return this.image ? this.word.string : this.word.string.replace(FAKE_SOFT_HYPHEN, '');
      },
    },
  }
</script>

<style lang="scss" scoped>
  .current-word {
    border: 1px green solid !important;
  }
  .edited {
    border: 1px orange solid !important;
    &.current-word {
      outline: 1px green solid !important;
    }
  }
</style>
