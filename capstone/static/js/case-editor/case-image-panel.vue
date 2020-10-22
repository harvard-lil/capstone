<template>
  <div>
    <div id="imageControls" class="text-right viz-controls">
      <button @click="imageZoom+=0.1" class="toggle-btn off zoom-in"></button>
      <button @click="imageZoom-=0.1" class="toggle-btn off zoom-out"></button>
    </div>
    <div :style="{transform: `scale(${imageZoom})`, 'transform-origin': '0% 0% 0px'}">
      <div v-for="page in pages" :key="page.id" :class="{page: true, 'show-ocr': showOcr}">
        <img :src="`data:image/png;base64,${page.png}`" :width="page.width * page.scale" :height="page.height * page.scale">
        <!-- manually render each word instead of using a reactive component, for speed on large cases -->
        <span v-for="word in page.words"
              :key="word.id"
              :class="{
                'word': true,
                'footnote-mark': word.footnoteMark,
                'edited': word.string !== word.originalString,
                [`word-id-${word.id}`]: true,
              }"
              :style="{
                left: `${word.x * page.scale}px`,
                top: `${word.y * page.scale - word.yOffset * page.fontScale - 1}px`,  // -1 for top border
                'background-color': word.wordConfidenceColor,
                // font format is '<styles> <font size>/<line height> <font families>':
                font: `${word.font.styles} ${word.font.size * page.fontScale}px/${word.lineHeight * page.fontScale}px ${word.font.family}`,
              }"
              :data-id="word.id"
        >{{ word.string }}</span>
      </div>
    </div>
  </div>
</template>

<script>
  import { mapState } from 'vuex'

  export default {
    computed: mapState(['showOcr']),
    props: ['pages', 'pngs'],
    data() {
      return {
        imageZoom: 1.0,
      }
    },
  }
</script>

<style lang="scss" scoped>
  .page {
    position: relative;
    span {
      border: 1px transparent solid;
      line-height: 1;
      color: transparent;
      position: absolute;
    }
    &.show-ocr {
      img {
        opacity: 0.2;
      }
      span {
        color: unset;
      }
    }
  }
</style>
