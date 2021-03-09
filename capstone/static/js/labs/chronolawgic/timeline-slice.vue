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
           data-toggle="modal"
           :data-target="$store.state.isAuthor ? '#add-event-modal' : '#readonly-modal'"
      @click="handleClick(event_data)">
      </div>
    </div>
  </div>
</template>

<script>
import {EventBus} from "./event-bus.js"

export default {
  name: "TimelineSlice",
  props: ['year_value', 'event_list'],
  methods: {
    openModal(item) {
      EventBus.$emit('openModal', item, 'event')
    },
    closeModal() {
      this.$emit('closeModal')
    },
    handleClick(event_data) {
      if (this.$store.state.isAuthor) {
        this.openModal(event_data)
      } else {
        this.toggleEventPreview(event_data)
      }
    },
    toggleEventPreview(event_data) {
      this.$parent.previewEvent(event_data);
    }
  },
}
</script>
