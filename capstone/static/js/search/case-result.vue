<template>
  <li class="result">
    <div class="result-title row">
      <div class="col-md-9">

        <a target="_blank" class="simple"
           :href="result.frontend_url">
          {{result.name_abbreviation}}
        </a>
      </div>
      <div class="col-md-3 decision-date">
        {{ formatDate(result.decision_date) }}
      </div>
    </div>
    <div class="row">
      <span v-for="(citation, index) in result.citations"
            v-bind:key="citation.cite"
            class="result-citation">
        {{ citation.cite }}<span v-if="index+1 < result.citations.length">, </span>
      </span>
      <span class="court" target="_blank"
            v-if="result.court">
      &nbsp;&middot;
        <a class="simple" :href="result.court.url">
          {{ result.court.name }}
        </a>
      </span>
      <span class="jurisdiction">
        &nbsp;&middot;
        <a class="simple" target="_blank" :href="result.jurisdiction.url">
          {{result.jurisdiction.name_long}}
        </a>
      </span>
    </div>
  </li>
</template>

<script>
  module.exports = {
    props: [
      'result'
    ],
    methods: {
      formatDate(dateStr) {
        /*
          Format a date string of any precision:
            1999-02-10 becomes February 10, 1999
            1999-02    becomes February 1999
            1999       becomes 1999
        */
        const patch = '0000-01-01';
        const patchedDateStr = dateStr + patch.slice(dateStr.length);
        const parsedDate = new Date(patchedDateStr);
        const formatOptions = {timeZone: "UTC", year: "numeric"};
        if (dateStr.length > 4)
          formatOptions.month = "long";
        if (dateStr.length > 7)
          formatOptions.day = "numeric";
        return parsedDate.toLocaleDateString(undefined, formatOptions);
      }
    }
  }
</script>