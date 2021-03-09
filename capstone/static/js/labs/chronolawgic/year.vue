<template>
  <div class="year" v-bind:class="{
    no_content_year: noContent,
    cases_only_year: casesWithoutEvents,
    events_only_year: eventsWithoutCases,
    cases_and_events_year: casesAndEvents
  }">
    <div class="incidental">

      <case v-for="case_data in year_data.case_list" :year_value="year_value" :case_data="case_data"
            v-bind:key="case_data.id"></case>
    </div>
    <div class="year_scale">
      <div class="left-line">
        <hr class="left-rule">
      </div>
      <div class="year">
        {{ year_value }}
      </div>
      <div class="right-line">
        <hr>
      </div>
    </div>
    <TimeLineSlice :event_list="year_data.event_list" :year_value="year_value"></TimeLineSlice>
    <template v-if="!$store.state.isAuthor">
      <event-preview :event="event"></event-preview>
    </template>
  </div>
</template>

<script>
import TimeLineSlice from './timeline-slice';
import Case from './case';
import EventPreview from "./EventPreview";
import {EventBus} from "./event-bus";

export default {
  name: "Year",
  components: {
    TimeLineSlice,
    Case,
    EventPreview

  },
  data() {
    return {
      event_count: this.year_data.event_list.reduce((acc, element) => acc + Object.keys(element).length, 0),
      event: null
    }
  },
  props: ['year_data', 'year_value'],
  computed: {
    noContent: function () {
      return (this.event_count + this.year_data.case_list.length === 0)
    },
    casesWithoutEvents: function () {
      return (this.event_count === 0 && this.year_data.case_list.length > 0)
    },
    eventsWithoutCases: function () {
      return (this.event_count > 0 && this.year_data.case_list.length === 0)
    },
    casesAndEvents: function () {
      return (this.event_count > 0 && this.year_data.case_list.length > 0)
    }
  },
  methods: {
    repopulateTimeline() {
      this.$parent.repopulateTimeline();
    },
    previewEvent(event_data) {
      this.event = event_data
      EventBus.$emit('closePreview', this.year_value);
    },
    clearPreviewEvent() {
      this.event = null;
    },
    openModal(item) {

      this.clearPreviewEvent()
      EventBus.$emit('openModal', item, 'event')
    },

  },
  mounted() {
    EventBus.$on('closePreview', (year_value) => {
      if (this.year_value !== year_value) {
        this.event = null;
      }
    })
  }
}
</script>

<style scoped>

</style>