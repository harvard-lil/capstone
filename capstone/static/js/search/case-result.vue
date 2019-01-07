<template>
  <li class="result">
    <div class="result-title row">
      <div class="row">
        <a target="_blank" v-text="result.name_abbreviation" :href="$parent.case_view_url(result.id)"></a>
      </div>
    </div>
    <div class="result-data">
      <div class="row">
        <div class="col-12">
          <ul class="citation-list">
            <li class="citation-entry" v-for="citation in result.citations">
              <span class="result-citation-type">{{  citation.type  }}</span>
              <span class="result-citation">{{ citation.cite }} </span>
            </li>
          </ul>
        </div>
      </div>
      <div class="row">
        <div class="col-3">{{ result.decision_date }}</div>
        <div class="col-4" v-if="result.court">{{ result.court.name }}, volume {{ result.jurisdiction.volume_number }}
        </div>
      </div>
      <div class="row">
        <div v-text="result.name" class="full-name col-12"></div>
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