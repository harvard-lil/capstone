<template>
  <div>
    <div v-for="opinion in opinions" :key="opinion.id" class="opinion">
      <!-- main text -->
      <h4 class="opinion-title">opinion: {{opinion.type}}</h4>
      <Paragraph v-for="paragraph in opinion.paragraphs"
                 :key="paragraph.id"
                 :paragraph="paragraph"
      ></Paragraph>
      <!-- footnotes -->
      <div v-if="opinion.footnotes && opinion.footnotes.length">
        <h4 class="opinion-title">footnotes: {{opinion.type}}</h4>
        <div v-for="footnote in opinion.footnotes" :key="footnote.id">
          <span>{{footnote.label}}</span>
          <Paragraph v-for="paragraph in footnote.paragraphs"
                     :key="paragraph.id"
                     :paragraph="paragraph"
          ></Paragraph>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
  import Paragraph from './case-text-paragraph'

  export default {
    components: {Paragraph},
    props: ['opinions'],
  }
</script>

<style lang="scss" scoped>
  .opinion {
    hyphens: none;
    padding-bottom: 2em;
    padding-top: 2em;
    border-bottom: 1px gray solid;
  }
  .footnote-mark {
    font-size: .83em;
    vertical-align: super;
  }
</style>