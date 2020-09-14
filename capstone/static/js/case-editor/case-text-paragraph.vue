<template>
  <div class="paragraph">
    <span class="paragraph-class">{{paragraph.class}}</span>
    <template v-for="block in paragraphBlocks()"
      ><Word v-for="word in block.words"
             :key="word.id"
             :image="false"
             :wordId="word.id"
      ></Word
    ></template>
  </div>
</template>

<script>
  import Word from './word.vue'

  export default {
    components: {Word},
    props: ['paragraph'],
    methods: {
      paragraphBlocks() {
        if (!this.paragraph.block_ids)
          return [];
        const blocksById = this.$root.$children[0].blocksById;
        return this.paragraph.block_ids.map(blockId => blocksById[blockId]);
      },
    }
  }
</script>

<style lang="scss" scoped>
  .paragraph {
    margin-bottom: 1em;
  }
  .paragraph-class {
    margin-right: 1em;
    color: gray;
  }
</style>