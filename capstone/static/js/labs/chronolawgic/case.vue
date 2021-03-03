<template>
  <article class="case" @click="openModal(case_data)" tabindex="0">
    <add-case-modal v-if="showEventDetails && $store.state.isAuthor"
                        data-toggle="modal"
                        data-target="add-case-modal"
                        :modal.sync="showEventDetails"
                        :case="event"
                        :shown="showEventDetails">
    </add-case-modal>
    <event-modal
        v-else-if="showEventDetails && !($store.state.isAuthor)"
        data-toggle="modal"
        data-target="event-modal"
        :modal.sync="showEventDetails"
        :event="event"
        :shown="showEventDetails">
    </event-modal>

    <header>
      {{ case_data.name }}
    </header>
    <section class="subhead">
      {{ case_data.subhead }}
    </section>
    <section class="desc">
      {{ case_data.short_description }}
    </section>
  </article>
</template>

<script>
import EventModal from './event-modal.vue';
// import EventAuthorModal from './event-author-modal.vue';
import AddCaseModal from "./add-case-modal";
export default {
  name: "Case",
  components: {AddCaseModal, EventModal},
  props: ['case_data', 'year_value'],
  data() {
    return {
      showEventDetails: false,
      event: {}
    }
  },
  methods: {
    openModal(item) {
      this.event = item;
      // this.event.decision_date = new Date(item.decision_date)
      this.showEventDetails = true;
    },
    closeModal() {
      this.showEventDetails = false
    },
    repopulateTimeline() {
      this.$parent.repopulateTimeline();
    }
  }

}
</script>

