<template>
  <div :class="{page: true, 'show-ocr': $parent.showOcr}">
    <img :src="page.image_url" :width="page.width * scale" :height="page.height * scale">
    <span v-for="(word, index) in words" :scroll-to-here="word.blockId + '_' + word.string" :key="index" :style="wordStyle(word)" @click="wordClicked(word)" :class="wordClass(word)">
      {{word.string}}
    </span>
  </div>
</template>

<script>
  import {FAKE_SOFT_HYPHEN, SOFT_HYPHEN} from "./helpers";

  export default {
    props: ['page', 'savedWordEdits'],
    data() {
      return {
        scale: 1,
        words: [],
      }
    },
    computed: {
      fontScale() {
        /*
          Conversion factor for font pts on scanned page to pixels.
          For example, a font detected as "12pt" in our 300DPI scan was actually 12/72 * 300 == 50px high.
        */
        return this.scale * 300/72;
      },
    },
    watch: {
      words: {
        handler() {
          this.$parent.saveStateToStorage();
        },
        deep: true
      },
    },
    beforeMount() {
      /*
        Extract a list of words from the token stream in this.page.blocks, and store the words in this.words.

        word objects look like this: {
          blockId,
          wordConfidence, font,  // display metadata
          x, y, w, h,  // location
          lineHeight, yOffset,  // calculated OCR alignment values
          strings: [{index, value}],  // list of the original token stream strings composing this word
          originalString,  // merged strings, before any edits
          string,  // merged strings, including any edits
        }

        To save changes later, we'll update `blocks[blockId].tokens[index]` to `string`, and empty any additional `strings`.
       */
      const words = [];
      for (const block of this.page.blocks) {
        if (!block.tokens)
          continue;
        let word = null;
        let fontId = -1;
        const savedWordEdits = this.savedWordEdits && this.savedWordEdits[block.id] ? this.savedWordEdits[block.id] : {};
        for (const [i, token] of block.tokens.entries()) {
          if (typeof token === 'string') {
            if (word)
              word.strings.push({index: i, value: token});
            continue;
          }
          const [tag, attrs] = token;
          if(tag === 'ocr') {
            const rect = attrs.rect;
            word = {
              blockId: block.id,
              wordConfidence: attrs.wc,
              font: this.$parent.fonts[fontId],
              strings: [],
              x: rect[0],
              y: rect[1],
              w: rect[2],
              h: rect[3],
            };
          } else if(tag === '/ocr') {
            if (!word)
              continue;  // tag closed before opened -- shouldn't happen
            if (word.strings.length) {
              // apply saved edits, if any
              const wordIndex = words.length;
              word.originalString = word.strings.map(s=>s.value).join("").replace(SOFT_HYPHEN, FAKE_SOFT_HYPHEN);
              if (wordIndex in savedWordEdits && savedWordEdits[wordIndex][0] === word.originalString)
                word.string = savedWordEdits[wordIndex][1];
              else
                word.string = word.originalString;

              // for OCR alignment, calculate line height based on font, and apply a y offset based on the tallest
              // character in the word
              word.lineHeight = this.$parent.getFontLineHeight(fontId);
              word.yOffset = Math.min(...word.string.split('').map(c => word.lineHeight - this.$parent.getCharAscent(c, fontId)));

              words.push(word);
            }
            word = null;
          } else if(tag === 'font') {
            fontId = attrs.id;
          } else if(tag === '/font') {
            fontId = -1;
          }
        }
      }
      this.words = words;
    },
    mounted() {
      this.scale = document.getElementById('canvas_div').offsetWidth / this.page.width;
    },
    methods: {
      wordStyle(word) {
        const font = word.font;
        return {
          left: `${word.x * this.scale}px`,
          top: `${word.y * this.scale - word.yOffset * this.fontScale - 1}px`,  // -1 for top border
          'background-color': this.$parent.showConfidence ? this.wordConfidenceColor(word) : 'unset',
          // font format is "<styles> <font size>/<line height> <font families>":
          font: `${font.styles} ${font.size * this.fontScale}px/${word.lineHeight * this.fontScale}px ${font.family}`,
        };
      },
      wordClass(word) {
        return {
          'current-word': this.$parent.currentWord === word,
          'edited': word.string !== word.originalString,
        };
      },
      wordClicked(word) {
        this.$parent.currentWord = word;
        this.$parent.currentPage = this;
        this.$nextTick(() => {
          this.$parent.$refs.currentWord.focus();
        });
      },
      wordConfidenceColor(word) {
        const alpha = (.6 - word.wordConfidence)*100;
        const red = 255 * word.wordConfidence + 127;
        return `rgba(${red}, 0, 0, ${alpha}%)`;
      },
    },
  }
</script>

<style lang="scss" scoped>
  .page {
    position: relative;
  }
  .page.show-ocr {
    img {
      opacity: 0.2;
    }
    span {
      color: unset;
    }
  }
  span {
    border: 1px transparent solid;
    line-height: 1;
    color: transparent;
    position: absolute;
  }
  .current-word {
    border: 1px green solid;
  }
  .edited {
    border: 1px orange solid;
  }
</style>
