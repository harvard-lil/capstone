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
        <div @submit.prevent="submitForm" class="modal-body">
          <div class="form-label-group" id="field-group-search">
            <input id="field-search-cap" placeholder="ENTER FULL TEXT OR CITATION" class="form-control">
            <label for="field-search-cap">ENTER FULL TEXT OR CITATION</label>
            <span><button role="button" class="btn btn-tertiary">SEARCH</button></span>
          </div>
          <div class="form-label-group" id="field-group-url">
            <input id="field-url" placeholder="URL" class="form-control">
            <label for="field-url">URL</label>
          </div>
          <div class="form-label-group" id="field-group-short">
            <input id="field-short-description" placeholder="SHORT DESCRIPTION" class="form-control">
            <label for="field-short-description">SHORT DESCRIPTION</label>
          </div>
          <div class="form-label-group" id="field-group-date">
            <input id="field-decision-date" placeholder="DECISION DATE" class="form-control">
            <label for="field-decision-date">DECISION DATE</label>
          </div>
          <div class="form-label-group" id="field-group-long">
            <textarea id="field-long-description" placeholder="LONGER DESCRIPTION"
                      class="form-control"></textarea>
          </div>
          <div class="form-label-group" id="field-group-jurisdiction">
            <input id="field-jurisdiction" placeholder="JURISDICTION" class="form-control">
            <label for="field-jurisdiction">JURISDICTION</label>
          </div>
          <div class="form-label-group" id="field-group-reporter">
            <input id="field-reporter" placeholder="REPORTER" class="form-control">
            <label for="field-reporter">REPORTER</label>
          </div>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-tertiary" data-dismiss="modal">Cancel</button>
          <button type="button" class="btn btn-primary">ADD</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from "axios";
import store from "./store";

export default {
  name: "add-case-modal",
  components: {},
  data() {
    return {
      newCase: {}
    }
  },
  methods: {
    submitForm() {
      console.log('submit form')
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
  },
}
</script>

<style scoped>

</style>