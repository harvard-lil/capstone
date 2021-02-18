<template>
  <main :class = "($store.getters.requestStatus === 'pending')?'loading':''">
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
  main.loading {
    background-color: lightgray;
  }
</style>