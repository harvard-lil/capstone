<template>
  <div v-if="$store.getters.showLoading" class="results-loading-container">
    <div class="row">
      <div class="col-11 col-centered">
        <img alt="" aria-hidden="true" :src='`${$store.getters.urls.static}img/loading.gif`' class="loading-gif"/>
        <div class="loading-text">Loading results...</div>
      </div>
    </div>
  </div>
  <div v-else-if="$store.getters.resultsShown"
       :class="['results-list-container', { 'results-shown': $store.getters.resultsShown}]">
    <div class="row">
      <div class="col-11 col-centered">
        <!-- show selected fields --->
        <div class="row">

          <ul class="col-9 list-inline field-choices">
            <li v-for="field in $store.getters.populated_fields" :key="'chosen' + field.name" class="list-inline-item field chosen-field">
              {{ field.label }}: {{ field.value }}
              <span class="reset-field" @click="$store.commit('clearFieldandSearch', field.name)">
                <close-icon class="close-icon"></close-icon>
              </span>
            </li>
          </ul>

          <template v-if="this.$store.getters.hitcount > 1">
                      <!-- show download options -->
            <div class="col-3 download-options-trigger text-right"
                 v-if="!toggle_download_options && $store.getters.resultsShown">
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
                         v-model="download_size"
                         id="max-downloads" :placeholder="download_size">

                  <label for="full-case">Full case</label>
                  <input v-model="download_full_case"
                         type="checkbox"
                         id="full-case">
                </div>

                <div class="col-6 text-right">
                  <div class="btn-group download-options row">

                    <div class="btn-group col-12">
                      <a class="btn-secondary download-formats-btn download-json"
                         target="_blank"
                         :href="$store.getters.download_url('json')"
                         title="Download JSON">
                        JSON
                      </a>
                      <a class="btn-secondary download-formats-btn download-csv"
                         :href="$store.getters.download_url('csv')"
                         title="Download CSV">
                        CSV
                      </a>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </template>
        </div>
        <template v-if="this.$store.getters.hitcount > 1">
          <div class="row">
                            <div class="hitcount col-6" id="results_count_focus" tabindex="-1">
                            <span class="results-count" v-if="this.$store.getters.hitcount < 1">No results</span>
                            <span class="results-count" v-else>
                            {{
                            first_result_number !== last_result_number ? `Results ${first_result_number} to ${last_result_number}` : `Result ${first_result_number}`
                            }}
                            of {{ $store.getters.hitcount }}
                            </span>
                            </div>
                            <div class="col-6 text-right" v-if="$store.getters.resultsShown">
                            <field-item :field="$store.getters.getField('ordering')" :search_on_change="true"></field-item>
                            </div>
                            </div>
          <ul class="results-list">
                                    <case-result v-for="result in $store.getters.results"
                                    :result="result"
                                    :key="'result_' + result.id">
                                    </case-result>
                                    </ul>
          <div class="row page-navigation-buttons" v-if="$store.getters.resultsShown">
                                                                                       <div class="col-6">
                                                                                       <button class="btn-secondary btn btn-sm" v-if="$store.getters.page > 1" @click="$store.dispatch('pageBackward')">
                                                                                       Prev: {{ $store.getters.page - 1 }} of {{ total_pages }}
                                                                                       </button>
                                                                                       <button class="btn-secondary btn btn-sm disabled" v-else disabled>Back</button>
                                                                                       </div>
                                                                                       <div class="col-6 text-right">
                                                                                       <button class="btn-secondary btn btn-sm" v-if="$store.getters.next_page_url" @click="$store.dispatch('pageForward')">
                                                                                       Next: {{ $store.getters.page + 1 }} of {{ total_pages }}
                                                                                       </button>
                                                                                       <button class="btn-secondary btn btn-sm disabled" v-else disabled>Next</button>
                                                                                       </div>
                                                                                       </div>
        </template>
        <template v-else>
          No Results
        </template>
      </div>
    </div>
  </div>
</template>


<script>
import CaseResult from './case-result.vue'
import CloseIcon from '../../../static/img/icons/close.svg';
import DownloadIcon from '../../../static/img/icons/download.svg';
import FieldItem from './field-item';

export default {
  data: function () {
    return {
      selected_fields: [],
      toggle_download_options: false,
    }
  },
  components: {
    CaseResult,
    CloseIcon,
    DownloadIcon,
    FieldItem,
  },
  computed: {
    first_result_number: function () {
      return this.$store.getters.page_size * (this.$store.getters.page - 1) + 1
    },
    last_result_number: function () {
      let last_number_full_page = this.$store.getters.page_size * this.$store.getters.page
      return this.$store.getters.hitcount > last_number_full_page ? last_number_full_page : this.$store.getters.hitcount
    },
    total_pages: function () {
      return  Math.ceil(this.$store.getters.hitcount/this.$store.getters.page_size)
    },
    download_full_case: {
        get () {
          return this.$store.getters.download_full_case;
        },
        set (value) {
          this.$store.commit('download_full_case', value)
        }
    },
    download_size: {
        get () {
          return this.$store.getters.download_size;
        },
        set (value) {
          this.$store.commit('download_size', value)
        }
    },
  },
}
</script>