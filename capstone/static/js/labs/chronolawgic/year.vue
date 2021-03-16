<template>
  <div class="year"
       v-bind:class="{
    no_content_year: noContent,
    cases_only_year: casesWithoutEvents,
    events_only_year: eventsWithoutCases,
    cases_and_events_year: casesAndEvents
  }" v-if="year_data.involvesAnyItem || !$store.getters.minimized">
    <div class="incidental">

      <case v-for="case_data in year_data.case_list" :year_value="year_value" :case_data="case_data"
            v-bind:key="case_data.id"></case>
    </div>
    <div class="year_scale" @mouseover="hoveringHandle(year_value, true)"
         @mouseleave="hoveringHandle(year_value, false)">
      <div class="left-line">
        <!-- if not author, show rule -->
        <hr class="left-rule" v-if="!$store.state.isAuthor || !showAddButton">
        <!-- if author, show + add case button on hover -->
        <template v-else-if="$store.state.isAuthor">

          <button @click="$parent.showAddCaseModal(true, {decision_date: year_value + '-01-01'})" v-if="$store.state.isAuthor" type="button"
                  class="btn btn-tertiary btn-add-event"
                  data-toggle="modal"
                  data-target="#add-case-modal">
            <add-icon></add-icon>
          </button>
        </template>
      </div>
      <div class="year">
        <div class="left-top"></div>
        <div class="right-top"></div>
        <div class="middle"><span>{{ year_value }}</span></div>
        <div class="left-bottom"></div>
        <div class="right-bottom"></div>
      </div>
      <div class="right-line">
        <hr v-if="!$store.state.isAuthor || !showAddButton">
        <template v-else-if="$store.state.isAuthor">
          <button @click="$parent.showAddEventModal(true, {start_date: year_value + '-01-01'})" v-if="$store.state.isAuthor" type="button"
                  class="btn btn-tertiary btn-add-event"
                  data-toggle="modal"
                  data-target="#add-event-modal">
            <add-icon></add-icon>
          </button>
        </template>
      </div>
    </div>
    <TimeLineSlice :event_list="year_data.event_list" :year_value="year_value"></TimeLineSlice>
    <template v-if="!$store.state.isAuthor">
      <event-preview :event="event"></event-preview>
    </template>
  </div>
  <div class="year placeholder"
       v-else-if="year_data.firstYearNoNewItems && !year_data.involvesAnyItem && $store.getters.minimized">
    <div class="incidental">
    </div>
    <div class="year_scale">
      <div class="left-line">
        <hr class="left-rule" v-if="!$store.state.isAuthor || !showAddButton">
        <template v-else-if="$store.state.isAuthor">
          <button @click="$parent.showAddCaseModal(true, {decision_date: year_value + '-01-01'})" v-if="$store.state.isAuthor" type="button"
                  class="btn btn-tertiary btn-add-event"
                  data-toggle="modal"
                  data-target="#add-case-modal">
            <add-icon class="add-icon"></add-icon>
            </button>
        </template>

      </div>
      <div class="year">
        <div class="left-top"></div>
        <div class="right-top"></div>
        <div class="middle">
          <span @click="$store.commit('toggleMinimized')"><more-vertical></more-vertical></span></div>
        <div class="left-bottom"></div>
        <div class="right-bottom"></div>
      </div>
      <div class="right-line">
        <hr v-if="!$store.state.isAuthor || !showAddButton">
        <template v-else-if="$store.state.isAuthor">
          <button @click="$parent.showAddEventModal(true, {start_date: year_value + '-01-01'})" v-if="$store.state.isAuthor" type="button"
                  class="btn btn-tertiary btn-add-event"
                  data-toggle="modal"
                  data-target="#add-event-modal">
            <add-icon class="add-icon"></add-icon>
          </button>
        </template>
      </div>
    </div>
  </div>
</template>

<script>
import AddIcon from '../../../../static/img/icons/plus-circle.svg';
import TimeLineSlice from './timeline-slice';
import Case from './case';
import EventPreview from "./EventPreview";
import {EventBus} from "./event-bus";
import MoreVertical from '../../../../static/img/icons/more-vertical.svg';

export default {
  name: "Year",
  components: {
    TimeLineSlice,
    Case,
    EventPreview,
    MoreVertical,
    AddIcon
  },
  data() {
    return {
      event_count: this.year_data.event_list.reduce((acc, element) => acc + Object.keys(element).length, 0),
      event: null,
      showAddButton: false,
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
    hoveringHandle(year_data, status) {
      this.showAddButton = status;
    }
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
