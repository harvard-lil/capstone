<template>
  <div class="spans row" @click="$store.commit('expandMobileEvents')">
    <div v-for="(event_data, index) in event_list" v-bind:key="year_value + index"
         :class="[ 'event_col', 'ec_' + (index + 1), 'col-1', 'e' + year_value, ]">
      <template v-if="$store.getters.isMobile && !$store.getters.mobileEventsExpanded">

        <div @click="$store.commit('expandMobileEvents')" :class="{
          'fill': true,
          'first-event-year': parseInt(year_value) === new Date(event_data.start_date).getUTCFullYear(),
          'last-event-year': parseInt(year_value) === new Date(event_data.end_date).getUTCFullYear(),
        }" v-if="Object.keys(event_data).length > 0"
             :tabindex="parseInt(year_value) === new Date(event_data.start_date).getUTCFullYear() ? '0' : '-1'"
             :style="{
                      'background-color': event_data.color,
                      'border-bottom': parseInt(year_value) === new Date(event_data.end_date).getUTCFullYear() ? '1rem solid gray' : '',
                      'min-height': '1rem'}">
        </div>

      </template>
      <template v-else>
        <div :class="{
          'fill': true,
          'first-event-year': parseInt(year_value) === new Date(event_data.start_date).getUTCFullYear(),
          'last-event-year': parseInt(year_value) === new Date(event_data.end_date).getUTCFullYear(),
        }" v-if="Object.keys(event_data).length > 0"
             :tabindex="parseInt(year_value) === new Date(event_data.start_date).getUTCFullYear() ? '0' : '-1'"
             :style="{
                      'background-color': event_data.color,
                      'border-bottom': parseInt(year_value) === new Date(event_data.end_date).getUTCFullYear() ? '1rem solid gray' : '',
                      'min-height': '1rem'
                  }"
             @click="openModal(event_data)"
             @blur="handleFocus(event_data)"
             @focus="handleFocus(event_data)"
             :data-toggle="$store.state.isAuthor ? 'modal' : ''"
             :data-target="$store.state.isAuthor ? '#add-event-modal': ''"
             :data-event-fill="event_data.id"
             :ref="fillRefGenerator(event_data, year_value)">
          <div class="event_label"
               :style="{'width': event_data.name.length + 'rem' }"
               v-if="parseInt(year_value) === new Date(event_data.start_date).getUTCFullYear()"
               v-text="event_data.name"
               :ref="'event-label' + event_data.id"
          ></div>

        </div>
      </template>
    </div>
  </div>
</template>

<script>

export default {
  name: "TimelineSlice",
  props: ['year_value', 'event_list'],
  methods: {
    closeModal() {
      this.$emit('closeModal')
    },
    openModal(event_data) {
      if (this.$store.state.isAuthor) {
        this.$parent.$parent.openModal(event_data, 'event')
      } else {
        this.toggleEventPreview(event_data, true)
      }
    },
    handleFocus(event_data) {
      this.toggleEventPreview(event_data, true)
    },
    handleBlur(event_data) {
      this.toggleEventPreview(event_data, false)
    },
    toggleEventPreview(event_data, open) {
      if (this.$store.state.isAuthor) return;
      if (open)
        this.$parent.previewEvent(event_data);
      else
        this.$parent.clearPreviewEvent()
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
  },
}
</script>
