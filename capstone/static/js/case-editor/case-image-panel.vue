<template>
  <div>
    <div id="imageControls" class="text-right viz-controls">
      <button @click="imageZoom+=0.1" class="toggle-btn off zoom-in"></button>
      <button @click="imageZoom-=0.1" class="toggle-btn off zoom-out"></button>
    </div>
    <div :style="{transform: `scale(${imageZoom})`, 'transform-origin': '0% 0% 0px'}">
      <div v-for="page in pages" :key="page.id" :class="{page: true, 'show-ocr': showOcr}">
        <img :src="page.image_url" :width="page.width * page.scale" :height="page.height * page.scale">
        <Word v-for="word in page.words"
              :key="word.id"
              :image="true"
              :wordId="word.id"
              :page="page"
        ></Word>
      </div>
    </div>
  </div>
</template>

<script>
  import { mapState } from 'vuex'

  import Word from './word'

  export default {
    components: {Word},
    computed: mapState(['showOcr']),
    props: ['pages'],
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
