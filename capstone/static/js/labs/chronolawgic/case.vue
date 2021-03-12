<template>
  <article class="case" @click="openModal(case_data)"
           data-toggle="modal"
           :data-target="$store.state.isAuthor ? '#add-case-modal' : '#readonly-modal'"
           tabindex="0">

    <header>
      <span class="case-name">{{ case_data.name }}</span>
      <a class="case-link" v-if="case_data.url"
         :href="case_data.url" target="_blank" @click.stop>
        <link-case/>
      </a>
    </header>
    <section class="desc">
      {{ case_data.short_description }}
    </section>
  </article>
</template>

<script>
import LinkCase from '../../../../static/img/icons/open_in_new-24px.svg';
import {EventBus} from "./event-bus.js";

export default {
  name: "Case",
  props: ['case_data', 'year_value'],
  components: {LinkCase},
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

