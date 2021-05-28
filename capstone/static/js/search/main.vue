<template>
  <div class="search-page">
    <div class="row">
      <search-form ref="searchform" :class="$store.getters.display_class"></search-form>
      <result-list :class="$store.getters.display_class"></result-list>
    </div>
  </div>
</template>


<script>
import SearchForm from './search-form.vue'
import ResultList from './result-list.vue'


export default {
  components: {SearchForm, ResultList},
  watch: {
    '$route': function () {
      this.$store.dispatch('searchFromParams');
    },
  },
  mounted() {
    this.$store.dispatch('searchFromParams');
  }
}
</script>