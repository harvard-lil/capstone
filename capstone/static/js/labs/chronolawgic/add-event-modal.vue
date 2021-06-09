<template>
  <div class="modal" id="add-event-modal" tabindex="-1" role="dialog" @click.stop>
    <div class="modal-dialog" role="document">
      <div class="modal-content">
        <div class="modal-header">
          <h5 class="modal-title" v-if="this.event && this.event.name">{{ this.event.name }}</h5>
          <h5 class="modal-title" v-else>ADD EVENT</h5>
          <button type="button" class="close" data-dismiss="modal" aria-label="Close" @click.stop="closeModal">
            <span aria-hidden="true">&times;</span>
          </button>
        </div>
        <div class="modal-body">
          <form @click.stop.prevent @submit.prevent="addEvent">
            <div class="form-label-group" id="field-group-name">
              <input v-model="newEvent.name" id="field-event-name" placeholder="NAME" required
                     class="form-control">
              <label for="field-event-name">EVENT NAME</label>
            </div>
            <div class="form-label-group" id="field-group-url">
              <input v-model="newEvent.url" id="field-event-url" placeholder="URL"
                     class="form-control">
              <label for="field-event-url">SOURCE URL</label>
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
            <textarea v-model="newEvent.long_description" id="field-event-long-description"
                      placeholder="LONGER DESCRIPTION"
                      class="form-control"></textarea>
            </div>
            <div class="form-label-group" id="field-group-end-date">
              <input v-model="newEvent.end_date" id="field-event-end-date" placeholder="DECISION DATE" type="date"
                     class="form-control">
              <label for="field-event-start-date">END DATE</label>
            </div>
            <v-select transition=""
                      class="color-dropdown"
                      label="color"
                      :filterable="false"
                      :clearable="false"
                      @input="setSelected"
                      v-model="newEvent.color"
                      :options="colors">
              <template #selected-option="{ color }">
                color: <span :style="{backgroundColor: color}" class="color-square">
                  {{ color }}
                </span>
              </template>
              <template #option="{ color }">
                <span :style="{backgroundColor: color}" class="color-square">
                  {{ color }}
                </span>
              </template>
            </v-select>
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
          <template v-if="this.event && this.event.id">
            <button type="button" class="btn btn-primary" @click="deleteEvent" data-dismiss="modal">
              Delete
            </button>
            <button type="button" class="btn btn-primary" @click.stop="updateEvent" data-dismiss="modal">
              Update
            </button>
          </template>
          <template v-if="!(this.event) || !(this.event.name)">
            <button type="button" class="btn btn-primary" @click.stop="addEvent"
                    :data-dismiss="$parent.showEvent ? 'none' : 'modal'">ADD
            </button>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import store from "./store";
import vSelect from 'vue-select'
import "vue-select/dist/vue-select.css";

export default {
  name: "add-event-modal",
  props: [
    'shown',
    'modal',
    'event'
  ],
  components: {
    vSelect
  },
  data() {
    return {
      colors: [],
      newEvent: {},
      errors: [],
    }
  },
  methods: {
    getRandomColor() {
      return this.colors[Math.floor(Math.random() * this.colors.length)]
    },
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
      if (new Date(this.newEvent.end_date) - new Date(this.newEvent.start_date) < 0) {
        this.errors.push('Start date must be earlier than end date.')
      }
      if (this.newEvent.url && !this.checkUrl(this.newEvent.url)) {
        if (!/^https?:\/\//i.test(this.newEvent.url) && this.checkUrl('https://' + this.newEvent.url)) {
            this.newEvent.url = 'https://' + this.newEvent.url;
        } else {
          this.errors.push('URL is not valid.')
        }
      }
    },
    closeModal() {
      this.$parent.closeModal();
      this.$parent.repopulateTimeline();
      this.setupEvent();
    },
    addEvent() {
      this.checkForm();
      if (this.errors.length) return;
      store.commit('addEvent', this.newEvent)
      this.closeModal();
    },
    deleteEvent() {
      store.commit('deleteEvent', this.event.id);
      this.closeModal();
    },
    updateEvent() {
      this.checkForm();
      if (this.errors.length) return;
      let event = this.unbind(this.newEvent)
      store.commit('updateEvent', event)
      this.closeModal()
    },
    unbind(obj) {
      return JSON.parse(JSON.stringify(obj))
    },
    setupEvent(existingEvent) {
      this.newEvent = existingEvent ? this.unbind(this.event) : this.unbind(store.getters.templateEvent);
      if (!this.newEvent.color)
        this.newEvent.color = this.getRandomColor();
    },
    setSelected(color) {
      this.newEvent.color = color
      // seems to be necessary because sometimes color is not updated when event exists
      this.newEvent = this.unbind(this.newEvent)
    },
    checkUrl(url) {
      try {
        new URL(url);
      } catch (e) {
        return false;
      }
      return url.includes('.');
    }
  },
  watch: {
    event(existingEvent) {
      this.setupEvent(existingEvent)
    },
  },
  mounted() {
    this.colors = store.getters.choices.colors;
    this.setupEvent(this.event)
  }
}
</script>
