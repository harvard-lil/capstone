<template>

  <div v-if="show_loading" class="results-loading-container col-centered">
    <img alt="" aria-hidden="true" :src='`${urls.static}img/loading.gif`' class="loading-gif"/>
    <div class="loading-text">Loading results ...</div>
  </div>
  <div v-else-if="results.length" class="results-list-container col-centered">
    <div class="hitcount">
      <span v-if="!results[page] || !results[page].length">No results</span>
      <span v-else>
        {{ first_result_number !== last_result_number ? `Results ${first_result_number} to ${last_result_number}` : `Result ${first_result_number}` }}
        of {{ hitcount ? hitcount.toLocaleString() : 'many' }}
      </span>
    </div>
    <ul class="results-list">
      <li v-if="endpoint==='cases'">
        <case-result v-for="result in results[page]"
                     :result="result"
                     :key="result.id">
        </case-result>
      </li>
      <li v-if="endpoint==='courts'">
        <court-result v-for="result in results[page]"
                      :result="result"
                      :key="result.id">
        </court-result>
      </li>
      <li v-if="endpoint==='jurisdictions'">
        <jurisdiction-result v-for="result in results[page]"
                             :result="result"
                             :key="result.id">
        </jurisdiction-result>
      </li>
      <li v-if="endpoint==='reporters'">
        <reporter-result v-for="result in results[page]"
                         :result="result"
                         :key="result.id">
        </reporter-result>
      </li>
    </ul>
    <div class="row">
      <div class="col-6">
        <button class="btn btn-sm" v-if="first_page !== true" @click="$emit('prev-page')">
          Back
        </button>
        <button class="btn btn-sm disabled" v-else disabled>Back</button>
      </div>
      <div class="col-6 text-right">
        <button class="btn btn-sm" v-if="last_page !== true" @click="$emit('next-page')">Page {{ page + 2 }}</button>
        <button class="btn btn-sm disabled" v-else disabled>Next</button>
      </div>
    </div>
  </div>
</template>


<script>
  import ReporterResult from './reporter-result.vue'
  import CaseResult from './case-result.vue'
  import CourtResult from './court-result.vue'
  import JurisdictionResult from './jurisdiction-result.vue'

  export default {
    props: [
      'results',
      'first_result_number',
      'last_result_number',
      'show_loading',
      'endpoint',
      'hitcount',
      'page',
      'first_page',
      'last_page',
      'urls'
    ],
    components: {
      'reporter-result': ReporterResult,
      'case-result': CaseResult,
      'court-result': CourtResult,
      'jurisdiction-result': JurisdictionResult,
    },
    methods: {
      case_view_url: function (case_id) {
        return this.urls.casemetadata_detail.replace('987654321', case_id)
      },
      metadata_view_url: function (endpoint, id) {
        return this.urls.view_court.replace('987654321', id).replace('/court/', "/" + endpoint + "/")
      }
    }
  }
</script>