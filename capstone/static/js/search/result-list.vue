<template>
  <div v-if="showLoading" class="results-loading-container">
    <div class="row">
      <div class="col-11 col-centered">
        <img alt="" aria-hidden="true" :src='`${urls.static}img/loading.gif`' class="loading-gif"/>
        <div class="loading-text">Loading results...</div>
      </div>
    </div>
  </div>
  <div v-else-if="resultsShown" class="results-list-container">
    <div class="row">
      <div class="col-11 col-centered">
        <!-- show selected fields --->
        <div class="row">
          <ul class="col-9 list-inline field-choices">
            <template v-for="field in chosen_fields">
              <li class="list-inline-item field chosen-field" v-if="field.value" v-bind:key="field.name">
                {{ field.label }}: {{ field.value }}
                <span class="reset-field" @click="reset_field(field.name)">
                  <close-icon class="close-icon"></close-icon>
                </span>
              </li>
            </template>
          </ul>
          <!-- show download options -->
          <div class="col-3 download-options-trigger text-right"
               v-if="resultsType==='cases' && !toggle_download_options && results[page] && results[page].length">
            <button class="btn btn-tertiary"
                    @click="toggle_download_options = !toggle_download_options">
              <download-icon class="download-icon"></download-icon>
              <br/>
              <span class="small">download</span>

            </button>
          </div>
          <div class="col-12 download-options-container" :class="toggle_download_options ? 'd-inline' : 'd-none'">
            <div class="row">
              <div class="col-10 download-title">
                <strong>Download options</strong>
              </div>
              <div class="col-2 text-right">
                <button class="btn btn-tertiary"
                        v-if="toggle_download_options"
                        @click="toggle_download_options = !toggle_download_options">
                  <close-icon class="close-icon"></close-icon>
                </button>
              </div>
            </div>
            <div class="row">
              <div class="col-6 download-options">
                <label for="max-downloads">Max amount</label>
                <input type="number"
                       v-model="local_page_size"
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
                       :href="downloadResults('csv')"
                       title="Download CSV">
                      CSV
                    </a>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
        <div class="row">
          <div class="hitcount col-6" id="results_count_focus" tabindex="-1">
            <span class="results-count" v-if="!results[page] || !results[page].length">No results</span>
            <span class="results-count" v-else>
                {{
                first_result_number !== last_result_number ? `Results ${first_result_number} to ${last_result_number}` : `Result ${first_result_number}`
              }}
                of {{ hitcount ? hitcount.toLocaleString() : 'many' }}
            </span>
          </div>
          <div class="col-6 text-right" v-if="results[page] && results[page].length">
            <field-item :field="sort_field" :hide_reset="true"></field-item>
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
    </div>
  </div>
</template>


<script>
import ReporterResult from './reporter-result.vue'
import CaseResult from './case-result.vue'
import CourtResult from './court-result.vue'
import JurisdictionResult from './jurisdiction-result.vue'
import CloseIcon from '../../../static/img/icons/close.svg';
import DownloadIcon from '../../../static/img/icons/download.svg';
import {EventBus} from "./event-bus";

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
      local_page_size: 10000,
      full_case: false,
      selected_fields: [],
      toggle_download_options: false,
    }
  },
  components: {
    ReporterResult,
    CaseResult,
    CourtResult,
    JurisdictionResult,
    CloseIcon,
    DownloadIcon,
  },
  methods: {
    metadata_view_url: function (endpoint, id) {
      return this.urls.view_court
          .replace('987654321', id)
          .replace('/court/', "/" + endpoint + "/")
    },
    reset_field: function (fieldname) {
      EventBus.$emit('resetField', fieldname)
    },
    downloadResults: function (format) {
      let full_case_string = ""
      if (this.full_case) {
        full_case_string = "&full_case=true"
      }
      return this.$parent.assembleUrl(this.local_page_size) + "&format=" + format + full_case_string;
    }
  }
}
</script>