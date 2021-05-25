<template>
  <div v-if="$store.getters.showLoading" class="results-loading-container">
    <div class="row">
      <div class="col-11 col-centered">
        <img alt="" aria-hidden="true" :src='`${$store.getters.urls.static}img/loading.gif`' class="loading-gif"/>
        <div class="loading-text">Loading results...</div>
      </div>
    </div>
  </div>
  <div v-else-if="$store.getters.resultsShown" class="results-list-container">
    <div class="row">
      <div class="col-11 col-centered">
        <!-- show selected fields --->
        <div class="row">


          <ul class="col-9 list-inline field-choices">
            <template v-for="field in $store.getters.populated_fields">
              <li class="list-inline-item field chosen-field" v-if="field.value" v-bind:key="field.name">
                {{ field.label }}: {{ field.value }}
                <span class="reset-field" @click="$store.commit('clearField', field.name)">
                  <close-icon class="close-icon"></close-icon>
                </span>
              </li>
            </template>
          </ul>


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
                       v-model="$store.download_size"
                       id="max-downloads" :placeholder="$store.download_size">

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
                       :href="$store.getters.download_url('json')"
                       title="Download JSON">
                      JSON
                    </a>&nbsp;
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
        </div>
        <div class="row">
          <div class="hitcount col-6" id="results_count_focus" tabindex="-1">
            <span class="results-count" v-if="!$store.getters.resultsShown">No results</span>
            <span class="results-count" v-else>
                {{
                $store.getters.first_result_number !== $store.getters.last_result_number ? `Results ${$store.getters.first_result_number} to ${$store.getters.last_result_number}` : `Result ${$store.getters.first_result_number}`
              }}
                of {{ $store.getters.hitcount }}
            </span>
          </div>
          <div class="col-6 text-right" v-if="$store.getters.resultsShown">
            <field-item :field="$store.getters.sort_field"></field-item>
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
              Prev: {{ $store.getters.page - 1 }} of {{ $store.getters.total_pages }}
            </button>
            <button class="btn-secondary btn btn-sm disabled" v-else disabled>Back</button>
          </div>
          <div class="col-6 text-right">
            <button class="btn-secondary btn btn-sm" v-if="$store.getters.next_page_url" @click="$store.dispatch('pageForward')">
              Next: {{ $store.getters.page + 1 }} of {{ $store.getters.total_pages }}
            </button>
            <button class="btn-secondary btn btn-sm disabled" v-else disabled>Next</button>
          </div>
        </div>
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
      full_case: false,
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
  methods: {
    updateOrdering: function () {
      //TODO start a fresh search
    }
  }
}
</script>