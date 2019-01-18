<template>
  <li class="result">
    <div class="result-title row">
      <div class="row"
           v-for="citation in result.citations">
        <a target="_blank"
           v-text="result.name_abbreviation"
           :href="$parent.case_view_url(result.id)"></a>

        <span v-if="citation.type === 'official'"
              class="result-citation">
          {{ citation.cite }}
        </span>
      </div>
    </div>
    <div class="result-data">
      <div class="row">
        <div v-text="result.name" class="full-name col-12"></div>
      </div>
      <div class="row">
        <div class="col-4" v-if="result.court">
          {{ result.court.name }}, volume {{ result.jurisdiction.volume_number }}
        </div>
        <div class="col-3">{{ result.decision_date }}</div>
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