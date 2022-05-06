<template>
  <div class="year"
       v-bind:class="{
          no_content_year: noContent,
          cases_only_year: casesWithoutEvents,
          events_only_year: eventsWithoutCases,
          cases_and_events_year: casesAndEvents}"
       :ref="year_value"
       v-if="year_data.involvesAnyItem || !$store.getters.minimized"
       @keydown.esc="clearPreviewEvent" :aria-label="year_value">
    <div v-if="$store.getters.isMobile && $store.getters.mobileEventsExpanded" class="incidental"
         @click="$store.commit('unExpandMobileEvents')">
      <div class="case_placeholder" v-if="year_data.case_list.length > 0">
        <more-horizontal></more-horizontal>
        <span class="case_count">{{ year_data.case_list.length }}</span>
      </div>
    </div>
    <div v-else class="incidental">
      <case v-for="case_data in year_data.case_list" :year_value="year_value" :case_data="case_data"
            v-bind:key="case_data.id"></case>
    </div>

    <!-- on mobile views, we're using a simple div.
    Replacing the year-label svg in the future might make sense. -->
    <div v-if="!$store.getters.isMobile" class="year_scale">
      <year-label :year="year_value"></year-label>
    </div>
    <div v-else class="year_scale">
      <div class="simple-mobile-year-label">{{ year_value }}</div>
    </div>
    <TimeLineSlice :event_list="year_data.event_list" :year_value="year_value"></TimeLineSlice>
  </div>
  <div class="year placeholder"
       v-else-if="year_data.firstYearNoNewItems && !year_data.involvesAnyItem && $store.getters.minimized">
    <div class="incidental" @click="$store.commit('unExpandMobileEvents')">
    </div>
    <div @click="$store.commit('toggleMinimized')" class="year_scale">
      <more-vertical></more-vertical>
    </div>
    <div class="spans" @click="$store.commit('expandMobileEvents')"></div>
  </div>
</template>

<script>
import TimeLineSlice from './timeline-slice.vue';
import Case from './case.vue';
import MoreVertical from '../../../../static/img/icons/more-vertical.svg';
import MoreHorizontal from '../../../../static/img/icons/more-horizontal.svg';
import YearLabel from './year-label'
import {EventBus} from "./event-bus";
import Vue from 'vue';

export default {
  name: "Year",
  components: {
    TimeLineSlice,
    Case,
    MoreVertical,
    MoreHorizontal,
    YearLabel,
  },
  data() {
    return {
      event_count: this.year_data.event_list.reduce((acc, element) => acc + Object.keys(element).length, 0),
      event: null,
      showAddButton: false,
    }
  },
  props: ['year_data', 'year_value', 'mobileEventsExpanded'],
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
    clearPreviewEvent() {
      this.event = null;
    },
  },
  mounted() {
    EventBus.$on('goToYear', (year) => {
      Vue.nextTick().then(() => {
        if (this.$refs[year]) {
          if (!this.$store.getters.isMobile)
            this.$el.scrollIntoView()
        }
      });
    })
  }
}
</script>