<template>
  <div v-if="showLoading" class="results-loading-container col-centered">
    <img alt="" aria-hidden="true" :src='`${urls.static}img/loading.gif`' class="loading-gif"/>
    <div class="loading-text">Loading results ...</div>
  </div>
  <div v-else-if="resultsShown" class="results-list-container col-centered">
    <div class="hitcount" id="results_count_focus" tabindex="-1">
      <span class="results-count" v-if="!results[page] || !results[page].length">No results</span>
      <span class="results-count" v-else>
        {{
          first_result_number !== last_result_number ? `Results ${first_result_number} to ${last_result_number}` : `Result ${first_result_number}`
        }}
        of {{ hitcount ? hitcount.toLocaleString() : 'many' }}
      </span>
      <div class="row download-button-set" v-if="resultsType==='cases'">
        <span class="title col-6">
          Download results
        </span>
        <div class="col-6 text-right">
          <div class="btn-group download-formats">
            <label for="max-downloads">Max</label>
            <input type="number"
                   v-model="localPageSize"
                   @change="updatePageSize"
                   id="max-downloads" placeholder="10000">
            <a class="btn-secondary"
               target="_blank"
               :href="downloadResults('json')"
               title="Download JSON">JSON</a>&nbsp;
            <a id="csv-download-button"
               class="btn-secondary download-csv"
               :href="downloadResults('csv')"
               title="Download tab separated CSV">tab separated CSV</a>
          </div>
        </div>

      </div>

    </div>
    <ul v-if="resultsType==='cases'" class="results-list">
      <case-result v-for="result in results[page]"
                   :result="result"
                   :key="result.id">
      </case-result>
    </ul>
    <ul v-else-if="resultsType==='courts'" class="results-list">
      <court-result v-for="result in results[page]"
                    :result="result"
                    :key="result.id">
      </court-result>
    </ul>
    <ul v-else-if="resultsType==='jurisdictions'" class="results-list">
      <jurisdiction-result v-for="result in results[page]"
                           :result="result"
                           :key="result.id">
      </jurisdiction-result>
    </ul>
    <ul v-else-if="resultsType==='reporters'" class="results-list">
      <reporter-result v-for="result in results[page]"
                       :result="result"
                       :key="result.id">
      </reporter-result>
    </ul>
    <div class="row page-navigation-buttons">
      <div class="col-6">
        <button class="btn-secondary btn btn-sm" v-if="first_page !== true" @click="$emit('prev-page')">
          Back
        </button>
        <button class="btn-secondary btn btn-sm disabled" v-else disabled>Back</button>
      </div>
      <div class="col-6 text-right">
        <button class="btn-secondary btn btn-sm" v-if="last_page !== true" @click="$emit('next-page')">
          Page {{ page + 2 }}
        </button>
        <button class="btn-secondary btn btn-sm disabled" v-else disabled>Next</button>
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
    'showLoading',
    'resultsShown',
    'resultsType',
    'endpoint',
    'hitcount',
    'page',
    'first_page',
    'last_page',
    'urls'
  ],
  data: function () {
    return {
      localPageSize: this.$parent.page_size,
    }
  },
  components: {
    'reporter-result': ReporterResult,
    'case-result': CaseResult,
    'court-result': CourtResult,
    'jurisdiction-result': JurisdictionResult,
  },
  methods: {
    metadata_view_url: function (endpoint, id) {
      let url = this.urls.view_court
          .replace('987654321', id)
          .replace('/court/', "/" + endpoint + "/")
      return url
    },
    updatePageSize: function () {
      this.$parent.page_size = this.localPageSize;
    },
    downloadResults: function (format) {
      return this.$parent.assembleUrl() + "&format=" + format;
    }
  }
}
</script>