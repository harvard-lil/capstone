<template>
  <div class="modal" id="add-case-modal" tabindex="-1" role="dialog">
    <div class="modal-dialog" role="document">
      <div class="modal-content">
        <div class="modal-header">
          <h5 class="modal-title">ADD CASE LAW</h5>
          <button type="button" @click="clearContent" class="close" data-dismiss="modal" aria-label="Close">
            <span aria-hidden="true">&times;</span>
          </button>
        </div>

        <div class="modal-body">
          <form @submit.prevent="searchCAP" id="form-search-cap">
            <div class="form-label-group" id="field-group-search">
              <input v-model="searchText" id="field-search-cap" placeholder="ENTER FULL TEXT OR CITATION"
                     class="form-control">
              <label for="field-search-cap">ENTER FULL TEXT OR CITATION</label>
              <span><button role="button" class="btn btn-tertiary" @click="searchCAP">SEARCH</button></span>
            </div>
            <ul v-if="searchResults.length" class="results-list">
              <span v-for="result in searchResults" @click="chooseCase(result)"
                    class="result-container"
                    :class="chosenCase.id === result.id ? 'chosen' : ''"
                    :key="result.id">
                <case-result :result="result">
              </case-result>
                </span>
            </ul>
            <div class="row" v-if="chosenCase">
              <button type="button" class="btn btn-tertiary" @click="autofillCase">AUTOFILL WITH CASE</button>
            </div>
          </form>
          <form @submit.prevent id="form-add-case">
            <!-- search results -->
            <div class="form-label-group" id="field-group-url">
              <input v-model="newCase.url" id="field-url" placeholder="URL" class="form-control">
              <label for="field-url">URL</label>
            </div>
            <div class="form-label-group" id="field-group-name">
              <input v-model="newCase.name" id="field-name" placeholder="CASE NAME" required class="form-control">
              <label for="field-url">CASE NAME</label>
            </div>
            <div class="form-label-group" id="field-group-short">
              <input v-model="newCase.short" id="field-short-description" placeholder="SHORT DESCRIPTION"
                     class="form-control">
              <label for="field-short-description">SHORT DESCRIPTION</label>
            </div>
            <div class="form-label-group" id="field-group-date">
              <input v-model="newCase.date" id="field-decision-date" placeholder="DECISION DATE" type="date" required
                     class="form-control">
              <label for="field-decision-date">DECISION DATE</label>
            </div>
            <div class="form-label-group" id="field-group-long">
            <textarea v-model="newCase.long" id="field-long-description" placeholder="LONGER DESCRIPTION"
                      class="form-control"></textarea>
            </div>
            <item-dropdown class="form-label-group" id="field-group-jurisdiction" :field="newCase.jurisdiction"
                           :display_value="newCase.jurisdiction.value ? newCase.jurisdiction.value : newCase.jurisdiction.label"
                           :choices="choices.jurisdictions">
            </item-dropdown>
            <item-dropdown class="form-label-group" id="field-group-reporter" :field="newCase.reporter"
                           :display_value="newCase.reporter.value ? newCase.reporter.value : newCase.reporter.label"
                           :choices="choices.reporters">
            </item-dropdown>

          </form>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-tertiary" @click="clearContent" data-dismiss="modal">Cancel</button>
          <button type="button" class="btn btn-primary" @click="addCase">ADD</button>
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
  data() {
    return {
      choices: {},
      searchResults: [],
      searchText: '',
      chosenCase: '',
      newCase: {
        url: "",
        name: "",
        short: "",
        long: "",
        date: "",
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
    addCase() {
      console.log("adding case", this.newCase)
    },
    chooseCase(result) {
      console.log("getting case", result)
      this.chosenCase = result;
    },
    autofillCase() {
      this.newCase.name = this.chosenCase.name_abbreviation;
      this.newCase.url = this.chosenCase.url;
      let date_parts = this.chosenCase.decision_date.split("-");

      // if day and/or month are absent, set to "01"
      let year = date_parts[0];
      let day = date_parts.length === 3 ? date_parts[2] : "01";
      let month = date_parts.length >= 2 ? date_parts[1] : "01";
      this.newCase.date = year + "-" + month + "-" + day;
      // this.newCase.jurisdiction.name = this.chosenCase.jurisdiction.slug
      this.newCase.jurisdiction.value = this.chosenCase.jurisdiction.name_long;
      this.newCase.reporter.value = this.chosenCase.reporter.full_name;
    },
    searchCAP() {
      //  this.chosen_fields = JSON.parse(JSON.stringify(this.fields))
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
      this.newCase = {
        url: "",
        name: "",
        short: "",
        long: "",
        date: "",
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
  mounted() {
    let url = store.state.urls.chronolawgic_api_retrieve.replace(":timeline_id", 1)
    axios
        .get(url)
        .then(response => response.data)
        .then(timeline => {
          console.log(timeline);
        })
    this.choices = store.state.choices
  },
}
</script>

<style scoped>

</style>