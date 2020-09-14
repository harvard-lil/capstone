<template>
  <div>
    <h4 class="section-title">case metadata</h4>
    <div class="row">
      <label class="col-8 m-0" for="metadata-human-corrected">Human Corrected</label>
      <input class="col-4" type="checkbox" v-model="human_corrected" id="metadata-human-corrected">
      <small class="form-text text-muted">Set "Human Corrected" if this case has been fully corrected and is essentially error-free.</small>
      <label class="col-4" for="metadata-name-abbreviation">Short Name</label>
      <input class="col-8" type="text" v-model="name_abbreviation" placeholder="case short name" id="metadata-name-abbreviation">
      <label class="col-4" for="metadata-name">Long Name</label>
      <input class="col-8" type="text" v-model="name" placeholder="case name" id="metadata-name">
      <label class="col-4" for="metadata-decision-date-original">Decision Date (YYYY-MM-DD)</label>
      <input class="col-8" type="text" v-model="decision_date_original" placeholder="decision date" id="metadata-decision-date-original">
      <label class="col-4" for="metadata-docket-number">Docket Number</label>
      <input class="col-8" type="text" v-model="docket_number" placeholder="docket number" id="metadata-docket-number">
    </div>
  </div>
</template>

<script>
  import { mapFields } from 'vuex-map-fields';

  export default {
    computed: mapFields([
      'metadata.human_corrected',
      'metadata.name_abbreviation',
      'metadata.name',
      'metadata.decision_date_original',
      'metadata.docket_number',
    ]),
  }
</script>
