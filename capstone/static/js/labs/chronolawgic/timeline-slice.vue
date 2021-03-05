<template>
  <div class="spans row">
    <div v-for="(event_data, index) in event_list" v-bind:key="year_value + index"
         :class="[ 'event_col', 'ec_' + (index + 1), 'col-1', 'e' + year_value, ]">
      <div class="fill" v-if="Object.keys(event_data).length > 0"
           :tabindex="parseInt(year_value) === new Date(event_data.start_date).getUTCFullYear() ? '0' : '-1'"
           :style="{
                    'background-color': event_data.color,
                    'border-top': parseInt(year_value) === new Date(event_data.start_date).getUTCFullYear() ? '1rem solid black' : '',
                    'border-bottom': parseInt(year_value) === new Date(event_data.end_date).getUTCFullYear() ? '1rem solid gray' : '',
                    'min-height': '1rem'
                }"
           @click.stop="openModal(event_data)">
        <add-event-modal v-if="showEventDetails && $store.state.isAuthor"
                            data-toggle="modal"
                            data-target="#add-event-modal"
                            :modal.sync="showEventDetails"
                            :event="event"
                            :shown="showEventDetails">
        </add-event-modal>
        <readonly-modal
            v-if="showEventDetails && !($store.state.isAuthor)"
            data-toggle="modal"
            data-target="#readonly-modal"
            :modal.sync="showEventDetails"
            :event="event"
            :shown="showEventDetails">
        </readonly-modal>
      </div>
    </div>
  </div>
</template>

<script>
import ReadonlyModal from "./readonly-modal";
import AddEventModal from "./add-event-modal";

export default {
  name: "TimelineSlice",
  components: {AddEventModal, ReadonlyModal},
  props: ['year_value', 'event_list'],
  methods: {
    openModal(item) {
      this.showEventDetails = true;
      this.event = item
    },
    closeModal() {
      this.showEventDetails = false
    },
    repopulateTimeline() {
      this.$parent.repopulateTimeline()
    }

  },
  data() {
    return {
      showEventDetails: false,
      event: {}
    }
  },
}
</script>

<style scoped>

</style>