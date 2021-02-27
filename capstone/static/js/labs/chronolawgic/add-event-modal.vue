<template>
  <div class="modal" id="add-event-modal" tabindex="-1" role="dialog">
    <div class="modal-dialog" role="document">
      <div class="modal-content">
        <div class="modal-header">
          <h5 class="modal-title">ADD EVENT</h5>
          <button type="button" class="close" data-dismiss="modal" aria-label="Close">
            <span aria-hidden="true">&times;</span>
          </button>
        </div>
        <div class="modal-body">
          <form @submit.prevent="addEvent">
            <div class="form-label-group">
              <input v-model="newEvent.name" id="field-event-name" placeholder="NAME" required
                     class="form-control">
              <label for="field-event-name">EVENT NAME</label>
            </div>
            <div class="form-label-group">
              <input v-model="newEvent.short_description" id="field-event-short-description"
                     placeholder="SHORT DESCRIPTION"
                     class="form-control">
              <label for="field-event-short-description">SHORT DESCRIPTION</label>
            </div>
            <div class="form-label-group">
              <input v-model="newEvent.start_date" id="field-event-start-date" placeholder="DECISION DATE" type="date"
                     required
                     class="form-control">
              <label for="field-event-start-date">START DATE</label>
            </div>
            <div class="form-label-group">
            <textarea v-model="newEvent.long" id="field-event-long-description" placeholder="LONGER DESCRIPTION"
                      class="form-control"></textarea>
            </div>
            <div class="form-label-group">
              <input v-model="newEvent.end_date" id="field-event-end-date" placeholder="DECISION DATE" type="date"
                     class="form-control">
              <label for="field-event-start-date">END DATE</label>
            </div>


          </form>
          <div v-if="errors.length" class="form-errors p-2 mt-2 small">
            <b>Please correct the following error(s):</b>
          <ul class="m-0 list-inline">
            <li class="list-inline-item" v-for="error in errors" v-bind:key="error">{{ error }}</li>
          </ul>
          </div>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-tertiary" @click="clearContent" data-dismiss="modal">Cancel</button>
          <button type="button" class="btn btn-primary" @click="addEvent">ADD</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import store from "./store";

export default {
  name: "add-event-modal",
  data() {
    return {
      newEvent: {},
      errors: [],
    }
  },
  methods: {
    clearContent() {
      this.newEvent = store.getters.templateEvent;
    },
    checkForm() {
      this.errors = [];
      if (!this.newEvent.name) {
        this.errors.push('Event name is required.');
      }
      if (!this.newEvent.start_date) {
        this.errors.push('Start date is required.');
      }
      if (!this.newEvent.end_date) {
        this.errors.push('End date is required.')
      }
    },
    addEvent() {
      this.checkForm();
      if (this.errors.length) return;

      if (typeof (this.newEvent.start_date) === 'string') {
        this.newEvent.start_date = new Date(this.newEvent.start_date)
      }
      if (typeof (this.newEvent.end_date) === 'string') {
        this.newEvent.end_date = new Date(this.newEvent.end_date)
      }
      store.commit('addEvent', this.newEvent)
      this.$parent.repopulateTimeline();
    }
  },
  mounted() {
    this.newEvent = store.getters.templateEvent;
  }
}
</script>

<style scoped>

</style>