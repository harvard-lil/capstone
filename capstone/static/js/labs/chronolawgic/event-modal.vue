<template>
  <div class="modal" id="event-modal" tabindex="-1" role="dialog">
    <div class="modal-dialog" role="document">
      <div class="modal-content">
        <div class="modal-header">
          <h5 class="modal-title">{{ event.name }} | {{ event.start_date}}</h5>
          <button type="button" class="close" @click="closeModal">
            <span aria-hidden="true">&times;</span>
          </button>
        </div>
        <div class="modal-body">
          <h6>{{ event.subhead }}</h6>
          <hr/>
          {{ event.long_description }}
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: "event-modal",
  props: [
      'showEventDetails',
      'shown',
      'modal',
      'event',
  ],
  methods: {
    closeModal() {
      this.$emit('toggleEventModal');
    }
  }
}
</script>

<style scoped>
#event-modal {
  display: block;
}
</style>