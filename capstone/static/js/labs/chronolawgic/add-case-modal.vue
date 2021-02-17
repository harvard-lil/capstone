<template>
  <div class="modal" id="add-case-modal" tabindex="-1" role="dialog">
    <div class="modal-dialog" role="document">
      <div class="modal-content">
        <div class="modal-header">
          <h5 class="modal-title">ADD CASE LAW</h5>
          <button type="button" class="close" data-dismiss="modal" aria-label="Close">
            <span aria-hidden="true">&times;</span>
          </button>
        </div>
        <form @submit.prevent class="modal-body">
          <div class="form-label-group" id="field-group-search">
            <input id="field-search-cap" placeholder="ENTER FULL TEXT OR CITATION" class="form-control">
            <label for="field-search-cap">ENTER FULL TEXT OR CITATION</label>
            <span><button role="button" class="btn btn-tertiary" @click="searchCAP">SEARCH</button></span>
          </div>
          <!-- search results -->
          <div class="search-results" v-if="searchResults.length"></div>
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
            <input v-model="newCase.date" id="field-decision-date" placeholder="DECISION DATE" type="date" required class="form-control">
            <label for="field-decision-date">DECISION DATE</label>
          </div>
          <div class="form-label-group" id="field-group-long">
            <textarea v-model="newCase.long" id="field-long-description" placeholder="LONGER DESCRIPTION"
                      class="form-control"></textarea>
          </div>
          <item-dropdown class="form-label-group" id="field-group-jurisdiction" :field="newCase.jurisdiction"
                         :choices="choices.jurisdictions">
          </item-dropdown>


          <div class="form-label-group" id="field-group-reporter">
            <input id="field-reporter" placeholder="REPORTER" class="form-control">
            <label for="field-reporter">REPORTER</label>
          </div>
        </form>
        <div class="modal-footer">
          <button type="button" class="btn btn-tertiary" data-dismiss="modal">Cancel</button>
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

export default {
  name: "add-case-modal",
  components: {
    ItemDropdown
  },
  data() {
    return {
      choices: {},
      searchResults: [],
      newCase: {
        url: "",
        short: "",
        long: "",
        date: "",
        jurisdiction: {
          name: 'jurisdiction',
          label: 'jurisdiction',
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
    searchCAP() {

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