<template>
  <article class="case" @click="toggleEventModal(case_data)" tabindex="0">
    <event-author-modal v-if="showEventDetails && $store.state.isAuthor"
                        data-toggle="modal"
                        data-target="event-author-modal"
                        :modal.sync="showEventDetails"
                        :event="event"
                        :shown="showEventDetails">
    </event-author-modal>
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
import EventAuthorModal from './event-author-modal.vue';
export default {
  name: "Case",
  components: {EventModal, EventAuthorModal},
  props: ['case_data', 'year_value'],
  data() {
    return {
      showEventDetails: false,
      event: {}
    }
  },
  methods: {
    toggleEventModal(item) {
      this.showEventDetails = !this.showEventDetails;
      this.event = item
    },
  }

}
</script>

