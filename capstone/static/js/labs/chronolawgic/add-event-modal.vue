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
      newEvent: {}
    }
  },
  methods: {
    clearContent() {
      console.log("clear")
      this.newEvent = store.getters.templateEvent;
    },
    addEvent() {
      console.log("add", this.newEvent)
      store.commit('addEvent', this.newEvent)

    }
  },
  mounted() {
    this.newEvent = store.getters.templateEvent;
  }
}
</script>

<style scoped>

</style>