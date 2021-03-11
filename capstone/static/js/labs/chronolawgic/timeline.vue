<template>
  <main id="main-app">
    <div class="row top-menu">
      <header class="header-section case-law-section">
        <h5>CASELAW</h5>
        <button @click="showAddCaseModal(true)" v-if="isAuthor" type="button"
                class="btn btn-tertiary btn-add-event"
                data-toggle="modal"
                data-target="#add-case-modal">
          <add-icon></add-icon>
        </button>
      </header>
      <header class="header-section other-events-section">
        <h5>EVENTS</h5>
        <button @click="showAddEventModal(true)" v-if="isAuthor" type="button"
                class="btn btn-tertiary btn-add-event"
                data-toggle="modal"
                data-target="#add-event-modal">
          <add-icon></add-icon>
        </button>
      </header>
    </div>
    <section id="timeline">
        <year v-for="(year_data, idx) in years" v-bind:key="'year_' + idx" :year_data="year_data" :year_value="idx"></year>
    </section>

    <!-- ALL MODALS -->
    <template v-if="$store.state.isAuthor">
      <add-case-modal v-if="showCase"
                      data-toggle="modal"
                      data-target="#add-case-modal"
                      :modal.sync="showCase"
                      :case="event"
                      :shown="showCase">
      </add-case-modal>
      <add-event-modal v-if="showEvent"
                       data-toggle="modal"
                       data-target="#add-event-modal"
                       :modal.sync="showEvent"
                       :event="event"
                       :shown="showEvent">
      </add-event-modal>
    </template>
    <!-- if user is not author of timeline, show readonly modal -->
    <template v-else>
      <readonly-modal
          v-if="showCase || showEvent"
          data-toggle="modal"
          data-target="#readonly-modal"
          :modal.sync="showEventDetails"
          :event="event"
          :shown="showEventDetails">
      </readonly-modal>
    </template>
  </main>

</template>
<script>
import AddIcon from '../../../../static/img/icons/add.svg';
import AddCaseModal from './add-case-modal.vue';
import AddEventModal from './add-event-modal.vue';
import ReadonlyModal from './readonly-modal.vue';
import Year from './year';
import {EventBus} from "./event-bus.js";


export default {
  name: 'Timeline',
  components: {
    AddIcon,
    AddCaseModal,
    AddEventModal,
    ReadonlyModal,
    Year,
  },
  computed: {
    title() {
      return this.$store.state.title
    },
    isAuthor() {
      return this.$store.state.isAuthor
    },
  },
  watch: {
    title() {
      this.repopulateTimeline();
    }
  },
  data() {
    return {
      checked: false,
      showCase: false,
      showEvent: false,
      showEventDetails: false,
      keyShown: false,
      years: {},
      event: null,
      events: [],
      cases: []
    }
  },
  methods: {
    check() {
      this.checked = !this.checked;
    },
    showAddEventModal(val) {
      this.event = null;
      this.showEvent = val;
      this.showEventDetails = this.showEvent
    },
    showAddCaseModal(val) {
      this.event = null;
      this.showCase = val;
      this.showEventDetails = this.showCase
    },
    closeModal() {
      this.showAddCaseModal(false)
      this.showAddEventModal(false)
      this.showEventDetails = false;
      this.event = null;
      EventBus.$emit('closeModal')
    },

    toggleKey() {
      this.keyShown = !this.keyShown;
    },
    repopulateTimeline() {
      /*
      there are certainly better ways to do this— this is just the way it came out for the MVP
       */

      const firstYear = this.$store.getters.firstYear;
      const finalYear = this.$store.getters.lastYear;

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
        if (newCases.length + newEvents.length === 0 && year > firstYear) {
            const lastYearECount = this.$store.getters.eventByStartYear(year - 1).length;
            const lastYearCCount = this.$store.getters.casesByYear(year - 1).length;

            console.log("wow", year, year - 1, firstYear, finalYear)
            console.log(this.$store.getters.casesByYear(year - 1))
            console.log(this.$store.getters.casesByYear(year))
            console.log(this.$store.getters.eventByStartYear(year))
            console.log(this.$store.getters.eventByStartYear(year - 1))
            console.log("then")
            this.$set(this.years[year], 'firstYearNoNewItems', lastYearECount + lastYearCCount > 0 )
        }

        if (newEvents.length > 0) {
          newEvents.forEach((evt) => {
            for (let track_index = 0; track_index < 12; track_index++) {
              if (Object.keys(this.years[year].event_list[track_index]).length === 0) { // since the events are start-year sorted, if the track is empty on the first year, it'll be good for the rest
                let length = new Date(evt.end_date).getUTCFullYear() - new Date(evt.start_date).getUTCFullYear();
                for (let event_year = 0; event_year <= length; event_year++) { // fill in the years on that track with the event
                  this.$set(this.years[year + event_year].event_list, track_index, evt);
                  this.$set(this.years[year + event_year], 'involvesAnyItem', true )
                  this.$set(this.years[year], 'firstYearNoNewItems', false )
                }
                return false // break
              }
            }
          });
        }
        
        
      }
    },
  },
  created() {
    EventBus.$on('openModal', (item, typeOfItem) => {
      this.showEvent = typeOfItem === 'event';
      this.showCase = typeOfItem === 'case';
      this.event = item;
    });
  }
};
</script>
