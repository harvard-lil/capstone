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

export default {
  name: 'Admin',
  components: {
  },

  data() {
    return {
    }
  },
  created() {
    this.$store.dispatch('requestTimelineList');
    if (Number.isInteger(this.$route.params.timeline)) {
      this.$store.dispatch('requestTimeline', this.$route.params.timeline);
    }
  }
};
</script>

<style>

</style>