<template>
  <div class="paragraph">
    <span class="paragraph-class">{{paragraph.class}}</span>
    <!-- manually render each word instead of using a reactive component, for speed on large cases -->
    <template v-for="block in paragraphBlocks()"
      ><span v-for="word in block.words"
             :key="word.id"
             :class="{
               'word': true,
               'footnote-mark': word.footnoteMark,
               'edited': word.string !== word.originalString,
               [`word-id-${word.id}`]: true,
             }"
             :style="{
               'background-color': word.wordConfidenceColor,
               font: `${word.font.textStyles} 1em sans-serif`,
               'font-family': 'inherit',
             }"
            :data-id="word.id"
        >{{ formatWord(word) }}</span
    ></template>
  </div>
</template>

<script>
  import {FAKE_SOFT_HYPHEN} from "static/js/case-editor/helpers";

  export default {
    props: ['paragraph'],
    methods: {
      paragraphBlocks() {
        if (!this.paragraph.block_ids)
          return [];
        const blocksById = this.$root.$children[0].blocksById;
        return this.paragraph.block_ids.map(blockId => blocksById[blockId]);
      },
      formatWord(word) {
        return word.string.replace(FAKE_SOFT_HYPHEN, '');
      }
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