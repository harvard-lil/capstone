<template>
  <li class="result">
    <div class="result-title row"
         v-for="citation in result.citations" v-bind:key="citation.cite">
      <a target="_blank"
         :href="$parent.case_view_url(result.id)">
        {{result.name_abbreviation}}
      </a>
      &nbsp; &nbsp;
      <span v-if="citation.type === 'official'"
            class="result-citation">
          {{ citation.cite }}
        </span>
    </div>

    <div class="row">
      <div class="full-name">
        {{result.name}}
      </div>
      <div class="court"
           v-if="result.court">
        {{ result.court.name }}
      </div>

    </div>
    <div class="row">
      <div class="decision-date">
        {{ result.decision_date }}
      </div>
      <div class="text-right volume">
        Volume {{ result.jurisdiction.volume_number }} 567
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