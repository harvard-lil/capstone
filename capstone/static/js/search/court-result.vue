<template>
  <li class="result">
    <div class="result-title row">
      <div class="row">
        <div class="result-title col-12">
          <a target="_blank" v-text="result.name_abbreviation"
             :href="$parent.metadata_view_url('court', result.id)"></a>
        </div>
      </div>
    </div>
    <div class="result-data">
      <div class="row">
        <div>
          <span class="result-data-label">Abbreviation:</span> {{ result.name_abbreviation }}
          <br/>
          <span class="result-data-label">Jurisdiction:</span> {{ result.jurisdiction }}
        </div>
        <div>
          <a href="#"
             class="see-cases"
             @click="$parent.$emit('see-cases', 'court', result.slug)">See cases</a>
        </div>
      </div>
    </div>
  </li>
</template>

<script>
  module.exports = {
    props: [
      'result'
    ],
  }
</script>