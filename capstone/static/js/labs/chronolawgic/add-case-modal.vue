<template>
  <div class="modal" id="add-case-modal" tabindex="-1" role="dialog">
    <div class="modal-dialog" role="document">
      <div class="modal-content">
        <div class="modal-header">
          <h5 class="modal-title">ADD CASE LAW</h5>
          <button type="button" @click.stop="closeModal" class="close" data-dismiss="modal" aria-label="Close">
            <span aria-hidden="true">&times;</span>
          </button>
        </div>
        <div class="modal-body">
          <form @submit.prevent="searchCAP" id="form-search-cap">
            <div class="form-label-group" id="field-group-search">
              <input v-model="searchText" id="field-search-cap" placeholder="ENTER FULL TEXT OR CITATION"
                     class="form-control">
              <label for="field-search-cap">ENTER FULL TEXT OR CITATION</label>
              <span class="button-container"><button role="button" class="btn btn-tertiary"
                                                     @click="searchCAP">SEARCH</button></span>
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
            <div class="row mb-4 mt-2" v-if="chosenCase && chosenCase.name_abbreviation">
              <button type="button" class="btn btn-tertiary pl-0 " @click="autofillCase">AUTOFILL WITH
                "{{ chosenCase.name_abbreviation.slice(0, 20) }}..."
              </button>
            </div>
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
              <input v-model="newCase.short_description" id="field-short-description" placeholder="SHORT DESCRIPTION"
                     class="form-control">
              <label for="field-short-description">SHORT DESCRIPTION</label>
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
          <button v-if="this.case" type="button" class="btn btn-primary" @click="deleteCase" data-dismiss="modal">Delete</button>
          <button type="button" class="btn btn-tertiary" @click.stop="closeModal" data-dismiss="modal">Cancel</button>
          <button v-if="this.case" type="button" class="btn btn-primary" @click.stop="updateCase"
                  data-dismiss='modal'>
            UPDATE
          </button>
          <button v-else type="button" class="btn btn-primary" @click="addCase"
                  data-dismiss="modal">
            ADD
          </button>
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

export default {
  name: "add-case-modal",
  components: {
    ItemDropdown,
    CaseResult
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
      searchText: '',
      chosenCase: {},
      newCase: {},
      errors: [],
      extraFields: { // need more info to interact with dropdown fields
        jurisdiction: {
          name: 'jurisdiction',
          label: 'jurisdiction',
          value: '',
        },
        reporter: {
          name: 'reporter',
          label: 'reporter',
          value: '',
        }
      }
    }
  },
  methods: {
    submitForm() {
      console.log('submit form')
    },
    checkForm() {
      this.errors = [];
      if (!this.newCase.name) {
        this.errors.push('Event name is required.');
      }
      if (!this.newCase.decision_date) {
        this.errors.push('Decision date is required.');
      }
    },
    closeModal() {
      console.log("calling parent closeModal")
      this.$parent.closeModal();
    },
    updateCase() {
      this.checkForm();
      if (this.errors.length) return;
      let caselaw = JSON.parse(JSON.stringify(this.newCase))
      this.case = this.newCase
      console.log("getting date:", caselaw.decision_date)
      store.commit('updateCase', caselaw)
      this.closeModal()
    },

    addCase() {
      this.checkForm();
      if (this.errors.length) return;
      let caselaw = JSON.parse(JSON.stringify(this.newCase))
      store.commit('addCase', caselaw);
      this.closeModal();
      this.$parent.repopulateTimeline();
    },
    deleteCase() {
      store.commit('deleteCase', this.case.id);
      this.closeModal();
      this.$parent.repopulateTimeline();
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
      this.newCase.url = this.chosenCase.url;
      this.newCase.decision_date = this.formatDate(this.chosenCase.decision_date);

      this.extraFields.jurisdiction.value = this.chosenCase.jurisdiction.name;
      this.extraFields.reporter.value = this.chosenCase.reporter.full_name;
    },
    searchCAP() {
      if (this.searchText) {
        let url = store.state.urls.api_root + "cases?search=" + this.searchText;
        axios.get(url)
            .then(response => response.data)
            .then(searchResponse => {
              this.searchResults = searchResponse.results;
            })
      }
    },
    clearContent() {
      this.closeModal();
      this.newCase = store.getters.templateCase;
    }
  },
  mounted() {
    this.choices = store.getters.choices;
    if (this.case) {
      // this.newCase = JSON.parse(JSON.stringify(this.case)) // deep copy to unbind
      this.newCase = this.case
    } else {
      this.newCase = store.getters.templateCase;
    }
  },
}
</script>
<style scoped>
#add-case-modal {
  display: block;
}
</style>