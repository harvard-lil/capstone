<template>
  <div v-if="showLoading" class="results-loading-container">
    <img alt="" aria-hidden="true" :src='`${urls.static}img/loading.gif`' class="loading-gif"/>
    <div class="loading-text">Loading results ...</div>
  </div>
  <div v-else-if="resultsShown" class="results-list-container">
    <!-- show selected fields --->
    <div class="field-choices">
      <div class="field" v-for="field in chosen_fields" v-bind:key="field.name">
        <span class="chosen-field" v-if="field.value">
          {{ field.name }} {{ field.value }}
          <span class="reset-field" @click="reset_field(field.name)">x</span>
        </span>
      </div>
    </div>
    <!-- show download options -->
    <div class="row download-button-set"
         v-if="resultsType==='cases' && results[page] && results[page].length">
      <div class="col-12 title">
        Download results
      </div>

      <div class="col-6 download-options">
        <label for="max-downloads">Max</label>
        <input type="number"
               v-model="local_page_size"
               @input="updatePageSize"
               id="max-downloads" :placeholder="local_page_size">

        <label for="full-case">Full case</label>
        <input v-model="full_case"
               type="checkbox"
               id="full-case">
      </div>

      <div class="col-6 text-right">
        <div class="btn-group download-options row">

          <div class="btn-group col-12">
            <a class="btn-secondary download-formats-btn download-json"
               target="_blank"
               :href="downloadResults('json')"
               title="Download JSON">
              JSON
            </a>&nbsp;
            <a class="btn-secondary download-formats-btn download-csv"
               :href="downloadResults('tsv')"
               title="Download tab separated CSV">
              TSV
            </a>
          </div>
        </div>
      </div>

    </div>
    <div class="hitcount" id="results_count_focus" tabindex="-1">
      <span class="results-count" v-if="!results[page] || !results[page].length">No results</span>
      <span class="results-count" v-else>
        {{
          first_result_number !== last_result_number ? `Results ${first_result_number} to ${last_result_number}` : `Result ${first_result_number}`
        }}
        of {{ hitcount ? hitcount.toLocaleString() : 'many' }}
      </span>
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
    <div class="row page-navigation-buttons" v-if="results[page] && results[page].length">
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
    'chosen_fields',
    'page',
    'first_page',
    'last_page',
    'urls',
  ],
  data: function () {
    return {
      local_page_size: this.$parent.page_size,
      full_case: false,
      selected_fields: [],
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
      return this.urls.view_court
          .replace('987654321', id)
          .replace('/court/', "/" + endpoint + "/")
    },
    updatePageSize: function () {
      this.$parent.page_size = this.local_page_size;
    },
    reset_field: function (fieldname) {
      this.$parent.reset_field(fieldname);
    },
    downloadResults: function (format) {
      let full_case_string = ""
      if (this.full_case) {
        full_case_string = "&full_case=true"
      }
      return this.$parent.assembleUrl() + "&format=" + format + full_case_string;
    }
  }
}
</script>