<template>
  <div class="modal" id="readonly-modal" tabindex="-1" role="dialog" @click.stop>
    <div class="modal-dialog" role="document">
      <div class="modal-content">
        <div class="modal-header">
          <h5 class="modal-title">{{ event.name }}</h5>
          <button type="button" class="close" @click.stop="closeModal" data-dismiss="modal" aria-label="Close">
            <span aria-hidden="true">&times;</span>
          </button>
        </div>
        <div class="modal-body">
          <article class="info">
            <p v-if="event.url">
              <span class="label">Source: </span>
              <a :href="event.url" target="_blank">{{ domain }}</a>
            </p>
            <p v-if="event.citation">
              <span class="label">Citation: </span>
              {{ event.citation }}
            </p>
            <p v-if="event.decision_date">
              <span class="label">Decision date: </span>
              {{ event.decision_date }}
            </p>
            <p v-if="event.start_date">
              <span class="label">Start date: </span>
              {{ event.start_date }}
            </p>
            <p v-if="event.end_date">
              <span class="label">End date: </span>
              {{ event.end_date }}
            </p>
            <p v-if="event.short_description"
               class="short-description">
              {{ event.short_description }}
            </p>
          </article>
          <hr v-if="event.short_description && event.long_description"/>
          <div class="long-description" v-if="event.long_description">
            <p v-for="(par, index) in event.long_description.split('\n')"
               :key="index">
              {{ par }}
            </p>
          </div>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-tertiary" @click.stop="closeModal" data-dismiss="modal">
            Close
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: "readonly-modal",
  props: [
    'modal',
    'event',
    'shown'
  ],
  data() {
    return {
      domain: ''
    }
  },
  methods: {
    closeModal() {
      this.$parent.closeModal();
    }
  },
  mounted() {
    if (this.event.url) {
      let domain = (new URL(this.event.url));
      this.domain = domain.hostname;
    }
  }
}
</script>

<style scoped>
</style>