<template>
  <div class="modal" id="add-event-modal" tabindex="-1" role="dialog" @click.stop>
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
            <div class="form-label-group" id="field-group-name">
              <input v-model="newEvent.name" id="field-event-name" placeholder="NAME" required
                     class="form-control">
              <label for="field-event-name">EVENT NAME</label>
            </div>
            <div class="form-label-group" id="field-group-short-description">
              <input v-model="newEvent.short_description" id="field-event-short-description"
                     placeholder="SHORT DESCRIPTION"
                     class="form-control">
              <label for="field-event-short-description">SHORT DESCRIPTION</label>
            </div>
            <div class="form-label-group" id="field-group-start-date">
              <input v-model="newEvent.start_date" id="field-event-start-date" placeholder="DECISION DATE" type="date"
                     required
                     class="form-control">
              <label for="field-event-start-date">START DATE</label>
            </div>
            <div class="form-label-group" id="field-group-long-description">
            <textarea v-model="newEvent.long_description" id="field-event-long-description" placeholder="LONGER DESCRIPTION"
                      class="form-control"></textarea>
            </div>
            <div class="form-label-group" id="field-group-end-date">
              <input v-model="newEvent.end_date" id="field-event-end-date" placeholder="DECISION DATE" type="date"
                     class="form-control">
              <label for="field-event-start-date">END DATE</label>
            </div>

            <item-dropdown class="form-label-group" id="field-group-color" :field="extraFields.colors"
                           :original_display_val="extraFields.colors.value ? extraFields.colors.value : extraFields.colors.label"
                           choices_type="colors"
                           :choices="choices.colors">
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
          <template v-if="this.event">
            <button type="button" class="btn btn-primary" @click="deleteEvent" data-dismiss="modal">
              Delete
            </button>
            <button type="button" class="btn btn-primary" @click.stop="updateEvent" data-dismiss="modal">
              Update
            </button>
          </template>
          <template v-if="!this.event">
            <button type="button" class="btn btn-primary" @click.stop="addEvent"
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
import ItemDropdown from "./item-dropdown"


export default {
  name: "add-event-modal",
  props: [
    'modal',
    'event'
  ],
  components: {
    ItemDropdown
  },
  data() {
    return {
      choices: {},
      newEvent: {},
      errors: [],
      extraFields: {
        colors: {
          name: 'color',
          label: 'color',
          value: ''
        }
      }
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
      event.color = this.extraFields.colors.value
      store.commit('updateEvent', event)
      this.closeModal()
      this.$parent.repopulateTimeline();
    },
  },
  mounted() {
    this.choices = store.getters.choices;
    if (this.event) {
      this.extraFields.colors.value = this.event.color
      this.newEvent = JSON.parse(JSON.stringify(this.event)) // deep copy to unbind
    } else {
      this.newEvent = JSON.parse(JSON.stringify(store.getters.templateEvent)); // deep copy to unbind
    }
  }
}
</script>
<style scoped>
#add-event-modal {
  display: block;
}
</style>