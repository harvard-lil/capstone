<template>
  <div class="modal" id="readonly-modal" tabindex="-1" role="dialog" @click.stop>
    <div class="modal-dialog" role="document">
      <div class="modal-content">
        <div class="modal-header">
          <h5 class="modal-title">{{ event.name }} | {{ event.start_date }}</h5>
          <button type="button" class="close" @click.stop="closeModal" data-dismiss="modal" aria-label="Close">
            <span aria-hidden="true">&times;</span>
          </button>
        </div>
        <div class="modal-body">
          <h6 v-if="event.short_description">{{ event.short_description }}</h6>
          <hr v-if="event.short_description"/>
          <div class="long-description" v-if="event.long_description">
            <p v-for="(par, index) in event.long_description.split('\n')"
               :key="index">
              {{ par }}
            </p>
          </div>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-tertiary" @click.stop="closeModal" data-dismiss="modal">
            Cancel
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
    'shown',
    'modal',
    'event',
  ],
  methods: {
    closeModal() {
      this.$parent.closeModal();
    }
  },
}
</script>

<style scoped>
#readonly-modal {
  display: block;
}
</style>