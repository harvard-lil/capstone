<template>
  <main id="main-app" ref="main-app-container" :class="{'mobile-event-expanded': $store.getters.mobileEventsExpanded }"
        @keyup.esc="handleEscape">
    <div class="row top-menu">
      <header :class="{ 'header-section': true, 'expanded': headerExpanded}">
        <h4 id="timeline-title" @click="toggleHeader()">{{ $store.state.title }}</h4>
        <div id="timeline-description" v-text="$store.state.description" @click="toggleHeader()"></div>
        <div class="my-timelines-link" v-if="$store.state.isAuthor">
          <router-link to="/">
            <ViewList></ViewList>
            my timelines
          </router-link>
        </div>
      </header>
      <div :class="{'header-section': true, 'zoom-section': true, 'expanded': headerExpanded}">
        <div class="empty-space"></div>
        <ul class="inline-list zoom-toggles">
          <li class="list-inline-item zoom-toggle zoom-in"
              :class="{selectable: !$store.state.minimized}"
              @click="$store.commit('toggleMinimized')">
            <minimize-icon></minimize-icon>
          </li>
          <li class="list-inline-item zoom-toggle zoom-out"
              :class="{selectable: $store.state.minimized}"
              @click="$store.commit('toggleMinimized')">
            <maximize-icon></maximize-icon>
          </li>
        </ul>
      </div>
    </div>
    <section id="timeline">
      <div class="row timeline-section-titles">
        <div class="caselaw-section" @click="$store.commit('unExpandMobileEvents')">
          <button v-if="$store.state.isAuthor" type="button"
                  @click="openModal(null, 'case')"
                  class="btn btn-tertiary btn-add-event"
                  data-toggle="modal"
                  data-target="#add-case-modal">
            <add-icon></add-icon>
          </button>
          <h6>CASELAW</h6>
        </div>
        <div class="other-events" @click="$store.commit('expandMobileEvents')">
          <div class="other-events-section">
            <h6>EVENTS</h6>
            <button v-if="this.$store.state.isAuthor"
                    @click="openModal(null, 'event')"
                    type="button"
                    class="btn btn-tertiary btn-add-event"
                    data-toggle="modal"
                    data-target="#add-event-modal">
              <add-icon class="add-icon"></add-icon>
            </button>
          </div>
        </div>
      </div>
      <year v-for="(year_data, idx) in years" v-bind:key="'year_' + idx"
            :year_data="year_data"
            :year_value="idx"></year>
    </section>

    <!-- ALL MODALS -->
    <add-case-modal v-if="showCase"
                    data-toggle="modal"
                    data-target="#add-case-modal"
                    :modal.sync="showCase"
                    :case="event"
                    :shown="showCase">
    </add-case-modal>
    <add-event-modal v-else-if="showEvent"
                     data-toggle="modal"
                     data-target="#add-event-modal"
                     :modal.sync="showEvent"
                     :event="event"
                     :shown="showEvent">
    </add-event-modal>
    <!-- if user is not author of timeline or on small screen, show readonly modal -->
    <readonly-modal
        v-if="showReadOnly"
        data-toggle="modal"
        data-target="#readonly-modal"
        :modal.sync="showReadOnly"
        :event="event"
        :shown="showReadOnly">
    </readonly-modal>
  </main>

</template>
<script>
import MinimizeIcon from '../../../../static/img/icons/minimize-2.svg';
import MaximizeIcon from '../../../../static/img/icons/maximize-2.svg';
import AddIcon from '../../../../static/img/icons/plus-circle.svg';
import AddCaseModal from './add-case-modal.vue';
import AddEventModal from './add-event-modal.vue';
import ReadonlyModal from './readonly-modal.vue';
import ViewList from '../../../../static/img/icons/view_list.svg';
import Year from './year';
import {EventBus} from "./event-bus.js";


export default {
  name: 'Timeline',
  components: {
    AddCaseModal,
    AddEventModal,
    AddIcon,
    ReadonlyModal,
    Year,
    MinimizeIcon,
    MaximizeIcon,
    ViewList
  },
  computed: {
    title() {
      return this.$store.state.title
    },
  },
  data() {
    return {
      headerExpanded: false,
      checked: false,
      showCase: false,
      showEvent: false,
      showReadOnly: false,
      keyShown: false,
      years: {},
      event: null,
      events: [],
      cases: [],
      windowWidth: window.innerWidth,
    }
  },
  watch: {
    title() {
      this.repopulateTimeline();
    },
    windowWidth(newWidth, oldWidth) {
      if (this.widthToBreakpoint(newWidth) !== this.widthToBreakpoint(oldWidth)) {
        this.$store.commit('setBreakPoint', this.widthToBreakpoint(newWidth));
      }
    }
  },
  methods: {
    check() {
      this.checked = !this.checked;
    },
    onResize() {
      this.windowWidth = window.innerWidth
    },
    openModal(item, typeOfItem) {
      this.showEvent = false;
      this.showCase = false;
      this.showReadOnly = false;
      this.event = null;

      if (item) {
        this.event = JSON.parse(JSON.stringify(item))
      }
      if (this.$store.state.isAuthor && !this.$store.getters.isMobile) {
        this.showEvent = typeOfItem === 'event';
        this.showCase = typeOfItem === 'case';
      } else {
        this.showReadOnly = true;
      }
    },
    closeModal() {
      this.showEvent = false;
      this.showCase = false;
      this.showReadOnly = false;
      this.event = null;
      EventBus.$emit('closeModal')
    },
    widthToBreakpoint(newWidth) {
      switch (true) {
        case (newWidth < 576):
          return "xs";
        case (newWidth < 768):
          return "sm";
        case (newWidth < 992):
          return "md";
        case (newWidth < 11200):
          return "lg";
        default:
          return "xl";
      }
    },
    toggleHeader() {
      this.headerExpanded = !this.headerExpanded;
    },
    toggleKey() {
      this.keyShown = !this.keyShown;
    },
    handleEscape() {
      EventBus.$emit('closePreview')
      this.closeModal();
    },
    repopulateTimeline() {
      /*
      there are certainly better ways to do this— this is just the way it came out for the MVP
       */

      const firstYear = this.$store.getters.firstYear;
      const finalYear = this.$store.getters.lastYear;

      // clear years
      this.years = {};

      // all the years need to be in place before the next loop because it does some logic based on future years
      for (let y = firstYear; y <= finalYear; y++) {
        this.$set(this.years, y, {
          case_list: [],
          event_list: Array(12).fill({}),
          firstYearNoNewItems: false,
          involvesAnyItem: false,
        })
      }

      for (let year = firstYear; year <= finalYear; year++) { // total range of timeline
        const newEvents = this.$store.getters.eventByStartYear(year); // events that start on this year
        const newCases = this.$store.getters.casesByYear(year); // cases that start on this year

        this.$set(this.years[year], 'case_list', newCases);

        // if there were cases and events last year but none this year, we want to mark it so we can add a placeholder
        if (newCases.length + newEvents.length > 0) {
          this.$set(this.years[year], 'involvesAnyItem', true)
        } else if (year > firstYear) {
          const lastYearECount = this.$store.getters.eventByStartYear(year - 1).length;
          const lastYearCCount = this.$store.getters.casesByYear(year - 1).length;
          this.$set(this.years[year], 'firstYearNoNewItems', lastYearECount + lastYearCCount > 0)
        }

        if (newEvents.length > 0) {
          newEvents.forEach((evt) => {
            for (let track_index = 0; track_index < 12; track_index++) {
              if (Object.keys(this.years[year].event_list[track_index]).length === 0) { // since the events are start-year sorted, if the track is empty on the first year, it'll be good for the rest
                let length = new Date(evt.end_date).getUTCFullYear() - new Date(evt.start_date).getUTCFullYear();
                for (let event_year = 0; event_year <= length; event_year++) { // fill in the years on that track with the event
                  this.$set(this.years[year + event_year].event_list, track_index, evt);
                  this.$set(this.years[year + event_year], 'involvesAnyItem', true)
                }
                return false // break
              }
            }
          });
        }
      }
    },
  },
  beforeDestroy() {
    window.removeEventListener('resize', this.onResize);
  },
  created() {
    EventBus.$on('openModal', (item, typeOfItem) => {
      this.openModal(item, typeOfItem);
    });
  },
  mounted() {
    this.$nextTick(() => {
      window.addEventListener('resize', this.onResize);
    });
    this.$store.commit('setBreakPoint', this.widthToBreakpoint(this.windowWidth))
  }
};
</script>
