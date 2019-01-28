<template>
  <li class="result">

    <div class="row">
      <div class="result-title col-12">
        <a target="_blank" v-text="result.name_long"
           :href="$parent.metadata_view_url('jurisdiction', result.id)"></a>
      </div>
    </div>

    <div class="result-data">
      <div class="row">
        <div class="">
          <span class="result-data-label">Abbreviation:</span>
          {{ result.name }}
          <br/>
          <span class="result-data-label">Slug:</span>
          {{ result.slug }}
        </div>
        <div>
          <a href="#"
             class="see-cases"
             @click="$parent.$emit('see-cases', 'jurisdiction', result.slug)">
            See cases
          </a>
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