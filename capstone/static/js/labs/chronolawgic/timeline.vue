<template>
  <main id="timeline-demo">
    <div class="row top-menu">
      <div class="header-section case-law-section">
        <span>CASE LAW</span>
        <button type="button" class="btn btn-tertiary" data-toggle="modal" data-target="#add-case-modal">
          <add-icon></add-icon>
        </button>
      </div>
      <div class="header-section other-events-section">
        <span>OTHER EVENTS</span>
        <button type="button" class="btn btn-tertiary" data-toggle="modal" data-target="#add-event-modal">
          <add-icon></add-icon>
        </button>
      </div>
      <div class="key-column">
        <button type="button" class="btn btn-tertiary">
          <key-icon @click="toggleKey"></key-icon>
        </button>
      </div>
    </div>
    <add-case-modal />
    <add-event-modal />
    <key v-show="keyShown"></key>
    <section id="timeline">
      <div v-for="(year_data, idx) in years" v-bind:key="idx">
        <year :year_data="year_data" :year_value="idx" v-if="idx > $store.getters.firstYear"></year>
      </div>
    </section>
  </main>

</template>
<script>
import KeyIcon from '../../../../static/img/icons/key.svg';
import AddIcon from '../../../../static/img/icons/add.svg';
import Key from './key.vue';
import AddCaseModal from './add-case-modal.vue';
import AddEventModal from './add-event-modal.vue';
import Year from './year';

export default {
  name: 'Timeline',
  components: {
    KeyIcon,
    AddIcon,
    Key,
    AddCaseModal,
    AddEventModal,
    Year,
  },

  data() {
    return {
      checked: false,
      title: 'Check me',
      addCaseModalShown: false,
      addEventModalShown: false,
      keyShown: false,
      years: {},
      eventsColorPool: [
        "#DB005B",
        "#DBC600",
        "#00B7DB",
        "#DB4500",
        "#3FDB00",
        "#0009DB",
        "#DB0C00",
        "#0073DB",
        "#CBDB00",
        "#8B00DB",
        "#DB8F00",
        "#00DB67"
      ],
    }
  },
  methods: {
    check() {
      this.checked = !this.checked;
    },
    showAddEventModal() {
      this.addEventModalShown = true;
    },
    toggleKey() {
      this.keyShown = !this.keyShown;
    },
    getDateRange() {
      this.$store.getters.events
    },
    repopulateTimeline() {
      /*
      there are certainly better ways to do this— this is just the way it came out for the MVP
       */

      for (let y = this.$store.getters.firstYear; y <= this.$store.getters.lastYear; y++) {
        this.$set(this.years, y, {
          case_list: this.$store.getters.casesByYear(y),
          event_list: [ {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {} ],
        })
      }

      for (let year = this.$store.getters.firstYear; year <= this.$store.getters.lastYear; year++) { // total range of timeline
        const newEvents = this.$store.getters.eventByStartYear(year); // events that start on this year
        if (newEvents.length > 0) {
          newEvents.forEach((evt) => {
            evt.color = this.eventsColorPool.pop()
            for (let track_index = 0; track_index < 12; track_index++){
              if (Object.keys(this.years[year].event_list[track_index]).length === 0) { // since the events are start-year sorted, if the track is empty on the first year, it'll be good for the rest
                let length = evt.end_year - evt.start_year;
                for (let event_year = 0; event_year <= length; event_year++) { // fill in the years on that track with the event
                   this.$set(this.years[year + event_year].event_list, track_index, evt)
                }
                return false // break
              }
            }
          });
        }
      }
    }
    // closeModal(e) {
    //   console.log("clicked", e)
    //   if (e.target !== $('div.modal-body')) {
    //     console.log("not modal-body")
    //   }
    // }
  },
  mounted: function () {
    this.repopulateTimeline();
  }
};
</script>
