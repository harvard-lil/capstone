<template>
  <div class="search-page">
    <div class="row">
      <search-form ref="searchform" :class="$store.getters.display_class">
      </search-form>
      <result-list :class="$store.getters.display_class"
                   :last_page="$store.getters.last_page"
                   :first_page="$store.getters.first_page"
                   :page="$store.getters.page"
                   :results="$store.getters.results"
                   :resultsShown="$store.getters.resultsShown"
                   :first_result_number="$store.getters.first_result_number"
                   :last_result_number="$store.getters.last_result_number"
                   :hitcount="$store.getters.hitcount"
                   :sort_field="$store.getters.sort_field"
                   :choices="$store.getters.choices"
                   :urls="$store.getters.urls">
      </result-list>
    </div>
  </div>
</template>


<script>
import SearchForm from './search-form.vue'
import ResultList from './result-list.vue'


export default {
  beforeMount: function () {
  },
  mounted: function () {
    //TODO read url state
  },
  watch: {
    results() {
      if (this.$store.getters.results.length && !this.$store.getters.resultsShown) {
        this.$store.commit('resultsShown', true)
      }
    },
    resultsShown() {
      let full_width = "col-md-12";
      this.$store.commit('display_class ', this.$store.getters.results.length ? "results-shown" : full_width);
    },
  },
  components: {SearchForm, ResultList},
  methods: {
    routeComparisonString(route) {
      /* Construct a stable comparison string for the given route, ignoring pagination parameters */
      if (!route) {
        return '';
      }
      const ignoreKeys = {cursor: true, page: true};
      const query = route.query;
      const queryKeys = Object.keys(query).filter(key => !ignoreKeys[key]);
      queryKeys.sort();
      return 'cases|' + queryKeys.map(key => `${key}:${query[key]}`).join('|');
    },
    handleRouteUpdate(route, oldRoute) {
      /*
        When the URL hash changes, update state:
        - set current endpoint
        - show appropriate fields
      */
      if (this.routeComparisonString(route) !== this.routeComparisonString(oldRoute)) {
        this.$store.resetSearchResults();
      }
    },

  },
}
</script>