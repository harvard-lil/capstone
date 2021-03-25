<template>
  <button class="case-button"
          type="button"
          @focus="handleFocus"
          @click="openModal(case_data)"
          data-toggle="modal"
          :data-target="dataTarget"
          tabindex="0">
    <article class="case">
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

  </button>
</template>

<script>
import LinkCase from '../../../../static/img/icons/open_in_new-24px.svg';
import {EventBus} from "./event-bus.js";

export default {
  name: "Case",
  props: ['case_data', 'year_value'],
  data() {
    return {
      dataTarget: '#readonly-modal'
    }
  },
  components: {LinkCase},
  methods: {
    openModal(item) {
      this.$parent.$parent.openModal(item, 'case')
    },
    closeModal() {
      EventBus.$emit('closeModal')
    },
    handleFocus() {
      EventBus.$emit('closePreview')
    },
    repopulateTimeline() {
      this.$parent.repopulateTimeline();
    }
  },
  beforeMount() {
    if (this.$store.getters.isMobile) {
      this.dataTarget = '#readonly-modal'
    } else if (this.$store.state.isAuthor) {
      this.dataTarget = '#add-case-modal'
    }
  }

}
</script>

