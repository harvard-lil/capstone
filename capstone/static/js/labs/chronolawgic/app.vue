<template>
    <main>
      <div v-if="$store.getters.requestStatus === 'pending'" id="loading"></div>
      <div v-if="$store.getters.notificationMessage">
          <div class="flash" v-if="$store.getters.requestStatus !== 'error'" id="success_msg">
              {{$store.getters.notificationMessage}}
          </div>
          <div class="flash" v-if="$store.getters.requestStatus === 'error'" id="error_msg">
              {{$store.getters.notificationMessage}}
          </div>
      </div>
        <router-view>

      </router-view>
    </main>

</template>

<script>
import $ from 'jquery';
import {EventBus} from "./event-bus.js";

export default {
  name: 'Admin',
  components: {
  },

  data() {
    return {
    }
  },
  created() {
    if (Number(this.$route.params.timeline)) {
      this.$store.dispatch('requestTimeline', this.$route.params.timeline);
    } else {
      this.$store.dispatch('requestTimelineList');
    }
    // hacky hack: we have to stop propagation to stop modal from reopening
    // and the backdrop therefore remains open
    EventBus.$on('closeModal', () => {
      $('.modal-backdrop').remove();
      $('body').removeClass('modal-open');
    })
  }
};
</script>
