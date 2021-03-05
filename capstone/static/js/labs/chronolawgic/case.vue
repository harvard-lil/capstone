<template>
  <article class="case" @click="openModal(case_data)"
           data-toggle="modal"
           :data-target="$store.state.isAuthor ? '#add-case-modal' : '#readonly-modal'"
           tabindex="0">

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
import {EventBus} from "./event-bus.js";

export default {
  name: "Case",
  props: ['case_data', 'year_value'],
  methods: {
    openModal(item) {
      EventBus.$emit('openModal', item, 'case')
    },
    closeModal() {
      EventBus.$emit('closeModal')
    },
    repopulateTimeline() {
      this.$parent.repopulateTimeline();
    }
  }

}
</script>

