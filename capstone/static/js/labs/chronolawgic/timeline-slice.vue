<template>
  <div class="spans row">
    <div v-for="(event_data, index) in event_list" v-bind:key="year_value + index"
         :class="[ 'event_col', 'ec_' + (index + 1), 'col-1', 'e' + year_value, ]">
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
        this.toggleEventPreview(event_data)
      }
    },
    handleFocus(event_data) {
      if (this.$store.state.isAuthor) return;
      this.toggleEventPreview(event_data)
    },
    toggleEventPreview(event_data) {
      this.$parent.previewEvent(event_data);
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
