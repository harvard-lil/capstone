<template>
  <div class="spans row" @click="$store.commit('expandMobileEvents')">
    <div v-for="(event_data, index) in event_list" v-bind:key="year_value + index"
         :title="event_data.name"
         :class="[ 'event_col', 'ec_' + (index + 1), 'col-1', 'e' + year_value, ]">
      <template v-if="$store.getters.isMobile && !$store.getters.mobileEventsExpanded">

        <div @click="$store.commit('expandMobileEvents')" :class="{
          'fill': true,
          'first-event-year': parseInt(year_value) === new Date(event_data.start_date).getUTCFullYear(),
          'last-event-year': parseInt(year_value) === new Date(event_data.end_date).getUTCFullYear(),
          'light-color': checkIfLight(event_data.color)
        }"
             v-if="Object.keys(event_data).length > 0"
             :tabindex="parseInt(year_value) === new Date(event_data.start_date).getUTCFullYear() ? '0' : '-1'"
             :style="{
                      'background-color': event_data.color,
                      'border-bottom': parseInt(year_value) === new Date(event_data.end_date).getUTCFullYear() ? '1rem solid gray' : '',
                      'min-height': '1rem'}">
        </div>

      </template>
      <template v-else>
        <button :class="{
          'fill': true,
          'first-event-year': parseInt(year_value) === new Date(event_data.start_date).getUTCFullYear(),
          'last-event-year': parseInt(year_value) === new Date(event_data.end_date).getUTCFullYear(),
          'light-color': checkIfLight(event_data.color)
        }"
             v-if="Object.keys(event_data).length > 0"
             :tabindex="parseInt(year_value) === new Date(event_data.start_date).getUTCFullYear() ? '0' : '-1'"
             :style="{
                      'background-color': event_data.color,
                      'border-bottom': parseInt(year_value) === new Date(event_data.end_date).getUTCFullYear() ? '1rem solid gray' : '',
                      'min-height': '1rem'
                  }"
             @click="openModal(event_data)"
             data-toggle="modal"
             :data-target="dataTarget"
             :data-event-fill="event_data.id"
             :ref="fillRefGenerator(event_data, year_value)">
          <div class="event_label"
               :style="{'width': setLabelWidth(event_data.end_date, event_data.start_date) }"
               v-if="parseInt(year_value) === new Date(event_data.start_date).getUTCFullYear()"
               v-text="event_data.name"
               :ref="'event-label' + event_data.id">
          </div>
        </button>
      </template>
    </div>
  </div>
</template>

<script>
import store from "./store";

export default {
  name: "TimelineSlice",
  props: ['year_value', 'event_list'],
  computed: {
    dataTarget: () => {
      // show readonly or event modal
      if (store.getters.isMobile || !store.state.isAuthor) {
        return '#readonly-modal'
      } else {
        return '#add-event-modal'
      }
    },
  },
  methods: {
    closeModal() {
      this.$emit('closeModal')
    },
    openModal(event_data) {
      this.$parent.$parent.openModal(event_data, 'event')
    },
    fillRefGenerator(event_data, year_value) {
      const firstEventYear = parseInt(year_value) === new Date(event_data.start_date).getUTCFullYear();
      const lastEventYear = parseInt(year_value) === new Date(event_data.end_date).getUTCFullYear();
      if (firstEventYear === year_value) {
        return "first_year_fill_" + event_data.id
      } else if (lastEventYear === year_value) {
        return "last_year_fill_" + event_data.id
      }
    },
    setLabelWidth(end_date, start_date) {
      // A small attempt at giving longer events longer title allotments
      let yearRange = new Date(end_date).getUTCFullYear() - new Date(start_date).getUTCFullYear()
      let base_size = 110 // px
      let width;
      width = yearRange * base_size
      width = width < base_size ? base_size : width
      return width + 'px'
    },
    checkIfLight(color) {
      // add class if font needs to be black
      let lightColors = ["#00db67", "#ccff6d", "#dbc600", "#db8f00"]
      return lightColors.indexOf(color.toLowerCase()) > -1
    }
  },
}
</script>
