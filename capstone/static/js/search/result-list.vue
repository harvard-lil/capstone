<template>

  <div class="results-list-container col-centered">

    <div class="hitcount" v-if="hitcount">
      <span v-if="hitcount > 1">{{hitcount}} results</span>
      <span v-else-if="hitcount===1">{{hitcount}} result</span>
      <span v-else>No results</span>
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
    <div v-if="this.$parent.results.length !== 0" class="row">
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
      'endpoint',
      'hitcount',
      'page',
      'first_page',
      'last_page',
      'case_view_url_template',
      'metadata_view_url_template'
    ],
    components: {
      'reporter-result': ReporterResult,
      'case-result': CaseResult,
      'court-result': CourtResult,
      'jurisdiction-result': JurisdictionResult,

    },
    methods: {
      case_view_url: function (case_id) {
        return this.case_view_url_template.replace('987654321', case_id)
      },
      metadata_view_url: function (endpoint, id) {
        return this.metadata_view_url_template.replace('987654321', id).replace('/court/', "/" + endpoint + "/")
      }

    }
  }
</script>