<template>
  <div class="modal" id="add-event-modal" tabindex="-1" role="dialog">
    <div class="modal-dialog" role="document">
      <div class="modal-content">
        <div class="modal-header">
          <h5 class="modal-title">ADD EVENT</h5>
          <button type="button" class="close" data-dismiss="modal" aria-label="Close" @click.stop="closeModal">
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
          <button type="button" class="btn btn-tertiary" @click.stop="closeModal" data-dismiss="modal">
            Cancel
          </button>
          <template v-if="this.event">
            <button type="button" class="btn btn-primary" @click="deleteEvent" data-dismiss="modal">
              Delete
            </button>
            <button type="button" class="btn btn-primary" @click.stop="updateEvent" data-dismiss="modal">
              Update
            </button>
          </template>
          <template v-if="!this.event">
            <button type="button" class="btn btn-primary" @click="addEvent"
                    :data-dismiss="$parent.addEventModalShown ? 'none' : 'modal'">ADD
            </button>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import store from "./store";

export default {
  name: "add-event-modal",
  props: [
    'showEventDetails',
    'modal',
    'event'
  ],
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
    closeModal() {
      this.$parent.closeModal();
    },

    addEvent() {
      this.checkForm();
      if (this.errors.length) return;

      store.commit('addEvent', this.newEvent)
      this.closeModal();
      this.$parent.repopulateTimeline();
    },
    deleteEvent() {
      store.commit('deleteEvent', this.event.id);
      this.closeModal();
      this.$parent.repopulateTimeline();
    },
    updateEvent() {
      this.checkForm();
      if (this.errors.length) return;
      let event = JSON.parse(JSON.stringify(this.newEvent))
      store.commit('updateEvent', event)
      this.closeModal()
      this.$parent.repopulateTimeline();
    },
  },
  mounted() {
    if (this.event) {
      this.newEvent = JSON.parse(JSON.stringify(this.event)) // deep copy to unbind
    } else {
      this.newEvent = store.getters.templateEvent;
    }
  }
}
</script>

<style scoped>
#add-event-modal {
  display: block;
}
</style>