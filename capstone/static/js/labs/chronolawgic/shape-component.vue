<template>
  <svg :width="width"
       :height="height"
       viewBox="0 0 80 80"
       :aria-labelledby="shapetype"
       fill="none" xmlns="http://www.w3.org/2000/svg">
    <title lang="en"
           v-text="title || shapetype + ' icon'">
    </title>
    <template v-if="shapetype==='circle'">
      <circle cx="33" cy="40" r="33" :fill="color"/>
    </template>
    <template v-else-if="shapetype==='polygon1'">
      <path d="M32.3588 2.55166C36.9151 -0.758709 43.0849 -0.758709 47.6412 2.55166L74.2053 21.8516C78.7616 25.162 80.6682 31.0297 78.9278 36.386L68.7812 67.614C67.0409 72.9703 62.0494 76.5967 56.4175 76.5967H23.5825C17.9506 76.5967 12.9591 72.9703 11.2188 67.614L1.0722 36.386C-0.668168 31.0297 1.23839 25.162 5.79472 21.8516L32.3588 2.55166Z"
            :fill="color"/>
    </template>
    <template v-else-if="shapetype==='polygon2'">
      <path d="M28.5 1.75278C32.5222 -0.569449 37.4778 -0.56945 41.5 1.75278L63.141 14.2472C67.1632 16.5694 69.641 20.8611 69.641 25.5056V50.4944C69.641 55.1389 67.1632 59.4306 63.141 61.7528L41.5 74.2472C37.4778 76.5694 32.5222 76.5694 28.5 74.2472L6.85898 61.7528C2.83677 59.4306 0.358982 55.1389 0.358982 50.4944V25.5056C0.358982 20.8611 2.83677 16.5694 6.85898 14.2472L28.5 1.75278Z" :fill="color"/>
    </template>
    <template v-else-if="shapetype==='rhombus'">
      <path d="M33.636 3.36396C37.1508 -0.150754 42.8492 -0.150758 46.364 3.36396L76.636 33.636C80.1508 37.1508 80.1508 42.8492 76.636 46.364L46.364 76.636C42.8492 80.1508 37.1508 80.1508 33.636 76.636L3.36396 46.364C-0.150754 42.8492 -0.150758 37.1508 3.36396 33.636L33.636 3.36396Z" :fill="color"/>
    </template>
    <template v-else-if="shapetype==='triangle'">
      <path d="M35.1362 4.5C38.6003 -1.5 47.2606 -1.5 50.7247 4.5L84.0666 62.25C87.5307 68.25 83.2006 75.75 76.2724 75.75H9.58846C2.66025 75.75 -1.66987 68.25 1.79423 62.25L35.1362 4.5Z" :fill="color"/>
    </template>
<!--    <template v-else-if="shapetype==='rectangle'">-->
<!--      <rect :width="width" :height="height" rx="10" :fill="color"/>-->
<!--    </template>-->
  </svg>

</template>

<script>

export default {
  name: "shape-component",
  props: ['shapetype', 'color', 'width', 'title'],

  data() {
    return {
      height: 30,
      ratios: {
        'circle': 1,
        'rhombus': 0.8,
        'polygon1': 0.85,
        'polygon2': 0.9,
        'triangle': 0.7,
        'rectangle': 1,
      }
    }
  },
  mounted() {
    this.height = this.width * this.ratios[this.shapetype]
  }
}
</script>
