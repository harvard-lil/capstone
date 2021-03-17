<template>
  <div class="modal" id="add-case-modal" tabindex="-1" role="dialog" @click.stop>
    <div class="modal-dialog" role="document">
      <div class="modal-content">
        <div class="modal-header">
          <h5 class="modal-title" v-if="this.case && this.case.name">{{ this.case.name }}</h5>
          <h5 class="modal-title" v-else>ADD CASELAW</h5>
          <button type="button" @click.stop="closeModal" class="close" data-dismiss="modal" aria-label="Close">
            <span aria-hidden="true">&times;</span>
          </button>
        </div>
        <div class="modal-body">
          <form @submit.stop id="form-search-cap" v-if="!this.case">
            <h6>Search CAP</h6>
            <div class="form-label-group" id="field-group-search">
              <input v-model="searchText" id="field-search-cap" placeholder="ENTER CITATION"
                     class="form-control">
              <label for="field-search-cap">SEARCH BY {{ extraFields.cap.value }}</label>
              <span>Search using:</span>
              <item-dropdown class="form-label-group" id="field-search-dropdown" :field="extraFields.cap"
                             :original_display_val="extraFields.cap.value ? extraFields.cap.value : extraFields.cap.label"
                             :choices="[['short name', 'short name'], ['citation', 'citation']]">
              </item-dropdown>

              <span class="button-container">
                <search-button :showLoading="showLoading"></search-button>
              </span>
            </div>
            <ul v-if="searchResults.length" class="results-list">
              <div v-for="result in searchResults" @click="chooseCase(result)"
                   class="result-container"
                   :class="chosenCase.id === result.id ? 'chosen' : ''"
                   :key="result.id">
                <case-result :result="result">
                </case-result>
              </div>
            </ul>
            <ul v-if="showNoSearchResults" class="results-list">
              <li class="result-container p-2">No results found</li>
            </ul>
            <div class="row mb-4 mt-2" v-if="chosenCase && chosenCase.name_abbreviation">
              <button type="button" class="btn btn-tertiary pl-0 " @click="autofillCase">AUTOFILL WITH
                "{{ chosenCase.name_abbreviation.slice(0, 20) }}..."
              </button>
            </div>
            <hr>
          </form>
          <form @submit.stop id="form-add-case">

            <!-- search results -->
            <div class="form-label-group" id="field-group-url">
              <input v-model="newCase.url" id="field-url" placeholder="URL" class="form-control">
              <label for="field-url">URL</label>
            </div>
            <div class="form-label-group" id="field-group-citation">
              <input v-model="newCase.citation" id="field-citation" placeholder="CITATION" class="form-control">
              <label for="field-citation">CITATION</label>
            </div>
            <div class="form-label-group" id="field-group-name">
              <input v-model="newCase.name" id="field-name" placeholder="CASE NAME" required class="form-control">
              <label for="field-name">CASE NAME</label>
            </div>
            <div class="form-label-group" id="field-group-short">
              <textarea v-model="newCase.short_description" id="field-short-description" placeholder="SHORT DESCRIPTION"
                        class="form-control"></textarea>
              <!--              <input v-model="newCase.short_description" id="field-short-description" placeholder="SHORT DESCRIPTION"-->
              <!--                     class="form-control">-->
            </div>
            <div class="form-label-group" id="field-group-date">
              <input v-model="newCase.decision_date" id="field-decision-date" placeholder="DECISION DATE" type="date"
                     required
                     class="form-control">
              <label for="field-decision-date">DECISION DATE</label>
            </div>
            <div class="form-label-group" id="field-group-long">
            <textarea v-model="newCase.long_description" id="field-long-description" placeholder="LONGER DESCRIPTION"
                      class="form-control"></textarea>
            </div>
            <item-dropdown class="form-label-group" id="field-group-jurisdiction" :field="extraFields.jurisdiction"
                           :original_display_val="extraFields.jurisdiction.value ? extraFields.jurisdiction.value : extraFields.jurisdiction.label"
                           :choices="choices.jurisdictions">
            </item-dropdown>
            <item-dropdown class="form-label-group" id="field-group-reporter" :field="extraFields.reporter"
                           :original_display_val="extraFields.reporter.value ? extraFields.reporter.value : extraFields.reporter.label"
                           :choices="choices.reporters">
            </item-dropdown>

          </form>
          <div v-if="errors.length" class="form-errors p-2 mt-2 small">
            <b>Please correct the following error(s):</b>
            <ul class="m-0 list-inline">
              <li class="list-inline-item" v-for="error in errors" v-bind:key="error">{{ error }}</li>
            </ul>
          </div>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-tertiary" @click.stop="closeModal" data-dismiss="modal">
            Cancel
          </button>
          <template v-if="this.case">
            <button type="button" class="btn btn-primary" @click="deleteCase" data-dismiss="modal">
              Delete
            </button>
            <button type="button" class="btn btn-primary" @click.stop="updateCase"
                    data-dismiss='modal'>
              Update
            </button>
          </template>
          <template v-if="!this.case">
            <button type="button" class="btn btn-primary btn-highlight" @click.stop="addCase"
                    data-dismiss="modal">
              ADD
            </button>
          </template>
        </div>
      </div>
    </div>

  </div>
</template>

<script>
import axios from "axios";
import store from "./store";
import ItemDropdown from "./item-dropdown"
import CaseResult from '../../search/case-result.vue'
import SearchButton from '../../vue-shared/search-button';

export default {
  name: "add-case-modal",
  components: {
    ItemDropdown,
    CaseResult,
    SearchButton
  },
  props: [
    'shown',
    'modal',
    'case'
  ],
  data() {
    return {
      choices: {},
      searchResults: [],
      showNoSearchResults: false,
      searchText: '',
      chosenCase: {},
      newCase: {},
      errors: [],
      extraFields: { // need more info to interact with dropdown fields
        jurisdiction: {
          name: 'jurisdiction',
          label: 'jurisdiction',
          value: 'jurisdiction',
        },
        reporter: {
          name: 'reporter',
          label: 'reporter',
          value: 'reporter',
        },
        cap: {
          name: 'search by',
          label: 'short name',
          value: 'short name'
        }
      },
      showLoading: false,
    }
  },
  methods: {
    checkForm() {
      this.errors = [];
      if (!this.newCase.name) {
        this.errors.push('Case name is required.');
      }
      if (!this.newCase.decision_date) {
        this.errors.push('Decision date is required.');
      }
    },
    closeModal() {
      this.$parent.closeModal();
      this.$parent.repopulateTimeline();
      this.setupDefaults();
    },
    updateCase() {
      this.checkForm();
      if (this.errors.length) return;
      let caselaw = this.unbind(this.newCase)
      caselaw.jurisdiction = this.extraFields.jurisdiction.value
      caselaw.reporter = this.extraFields.reporter.value
      store.commit('updateCase', caselaw)
      this.closeModal()
    },
    addCase() {
      this.checkForm();
      if (this.errors.length) return;
      let caselaw = this.unbind(this.newCase)
      caselaw.jurisdiction = this.extraFields.jurisdiction.value
      caselaw.reporter = this.extraFields.reporter.value
      store.commit('addCase', caselaw);
      this.closeModal();
    },
    deleteCase() {
      store.commit('deleteCase', this.case.id);
      this.closeModal();
    },
    chooseCase(result) {
      // choosing case from CAP search
      this.chosenCase = result;
    },
    formatDate(date) {
      // autofill missing month and day. Not ideal, but this is a timeline, after all.
      let date_parts = date.split("-");
      let year = date_parts[0];
      let day = date_parts.length === 3 ? date_parts[2] : "01";
      let month = date_parts.length >= 2 ? date_parts[1] : "01";
      return year + "-" + month + "-" + day;
    },
    autofillCase() {
      this.newCase.name = this.chosenCase.name_abbreviation;
      this.newCase.citation = this.chosenCase.citations[0].cite;
      this.newCase.url = this.chosenCase.frontend_url;
      this.newCase.decision_date = this.formatDate(this.chosenCase.decision_date);

      this.extraFields.jurisdiction.value = this.chosenCase.jurisdiction.name;
      this.extraFields.reporter.value = this.chosenCase.reporter.full_name;
    },
    searchCAP() {
      this.showNoSearchResults = false
      if (this.searchText) {
        this.showLoading = true;

        let query = this.extraFields.cap.value === 'citation' ? 'cite' : 'short_name'
        let url = store.state.urls.api_root + "cases?" + query + "=" + this.searchText;
        axios.get(url)
            .then(response => response.data)
            .then(searchResponse => {
              this.searchResults = searchResponse.results;
              if (this.searchResults.length === 0) {
                this.showNoSearchResults = true
              }
              this.showLoading = false;
            })
      }
    },
    valueUpdated() {
      this.searchCAP()
    },
    clearContent() {
      this.closeModal();
      this.newCase = store.getters.templateCase;
    },
    unbind(obj) {
      return JSON.parse(JSON.stringify(obj))
    },
    setupDefaults() {
      this.extraFields.jurisdiction.value = "jurisdiction"
      this.extraFields.reporter.value = "reporter"
      this.newCase = this.unbind(store.getters.templateEvent);
    },
    setupExisting() {
      this.newCase = this.unbind(this.case)
      this.extraFields.jurisdiction.value = this.newCase.jurisdiction
      this.extraFields.reporter.value = this.newCase.reporter
    }
  },
  watch: {
    case(existingCase) {
      if (existingCase && existingCase.id) {
        this.setupExisting();
      } else {
        this.setupDefaults();
      }
    }
  },
  mounted() {
    this.choices = store.getters.choices;
    if (this.case) {
      this.setupExisting()
    } else {
      this.setupDefaults();
    }
  },
}
</script>
<style scoped>
#add-case-modal {
  display: block;
}
</style>