<template>
  <div class="search-page">
    <div class="row">
      <search-form ref="searchform" v-on:new-search="newSearch" :class="$store.getters.display_class">
      </search-form>
      <result-list v-on:see-cases="seeCases"
                   v-on:next-page="nextPage"
                   v-on:prev-page="prevPage"
                   :class="$store.getters.display_class"
                   :last_page="$store.getters.last_page"
                   :first_page="$store.getters.first_page"
                   :page="$store.getters.page"
                   :results="$store.getters.results"
                   :resultsType="$store.getters.resultsType"
                   :resultsShown="$store.getters.resultsShown"
                   :first_result_number="$store.getters.first_result_number"
                   :last_result_number="$store.getters.last_result_number"
                   :endpoint="$store.getters.endpoint"
                   :hitcount="$store.getters.hitcount"
                   :chosen_fields="$store.getters.chosen_fields"
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
import {EventBus} from './event-bus.js';
import {encodeQueryData} from '../utils'

export default {
  beforeMount: function () {
  },
  mounted: function () {
    /* Read url state when first loaded. */
    this.$route ? this.handleRouteUpdate(this.$route) : this.updateSearchFormFields();
    EventBus.$on('resetField', (fieldname) => {
      this.reset_field(fieldname)
    })
  },
  watch: {
    /* Read url state on change. */
    '$route': function (route, oldRoute) {
      this.handleRouteUpdate(route, oldRoute);
    },
    results() {
      if (this.$store.getters.results.length && !this.$store.getters.resultsShown) {
        this.$store.commit('resultsShown', true)
      }
    },
    resultsShown() {
      let full_width = "col-md-12";
      this.$store.commit('display_class ', this.$store.getters.results.length ? "results-shown" : full_width);
    },
    endpoint() {
      this.$store.commit('fields', this.$store.getters.endpoints[this.$store.getters.endpoint]);
    }
  },
  components: {SearchForm, ResultList},
  data: function () {
    return {
      'test': 'test'
    }
  },
  methods: {
    reset_field(fieldname) {
      this.$store.getters.fields.map((f) => {
        if (f.name === fieldname) {
          f.value = "";
        }
      });
      this.assembleUrl();
      this.newSearch();
    },
    create_chosen_fields() {
      this.$store.getters.chosen_fields = JSON.parse(JSON.stringify(this.$store.getters.fields))
    },
    routeComparisonString(route) {
      /* Construct a stable comparison string for the given route, ignoring pagination parameters */
      if (!route) {
        return '';
      }
      const ignoreKeys = {cursor: true, page: true};
      const query = route.query;
      const queryKeys = Object.keys(query).filter(key => !ignoreKeys[key]);
      queryKeys.sort();
      return route.params.endpoint + '|' + queryKeys.map(key => `${key}:${query[key]}`).join('|');
    },
    updateSearchFormFields(query) {
      // load search fields and values from query params
      let fields = this.$store.getters.endpoints[this.$store.getters.endpoint];
      fields.forEach((field) => {
        if (field && query[field.name]) {
          field.value = query[field.name];
          fields[field] = field;
        }
      })
      this.$store.commit('fields', fields);
    },
    handleRouteUpdate(route, oldRoute) {
      /*
        When the URL hash changes, update state:
        - set current endpoint
        - show appropriate fields
      */
      const query = route.query;
      // if route changes (other than pagination), set endpoint and fields
      if (this.routeComparisonString(route) !== this.routeComparisonString(oldRoute)) {
        if (route.name) {
          // route can be unnamed, as in '/'
          this.$store.commit('endpoint', route.params.endpoint);
        }
        this.updateSearchFormFields(query);
        this.resetResults();
      }


      // handle page=n parameter: if it is 1 or greater, we show the requested search result page
      const newPage = query.page ? parseInt(query.page) - 1 : undefined;
      if (newPage >= 0) {
        this.$store.commit('page', newPage);
        if (query.cursor)
          this.$store.getters.cursors[this.$store.getters.page] = query.cursor; //SPECIAL

        // render results if we have enough information to do so:
        if (this.$store.getters.page === 0 || this.$store.getters.results[this.$store.getters.page] || this.$store.getters.cursors[this.$store.getters.page]) {
          this.getResultsPage().then(() => {
            this.scrollToResults();

            // set variables for pagination display -- result count and back and next buttons
            this.$store.getters.last_page = !this.$store.getters.cursors[this.$store.getters.page + 1];
            this.$store.getters.first_page = this.$store.getters.page === 0;
            this.$store.getters.first_result_number = 1 + this.$store.getters.page_size * this.$store.getters.page;
            this.$store.getters.last_result_number = this.$store.getters.first_result_number + this.$store.getters.results[this.$store.getters.page].length - 1;
          });
        }
      }
      this.create_chosen_fields();
    },
    newSearch() {
      // deep copy fields for displaying in results
      this.create_chosen_fields();
      this.goToPage(0)
    },
    nextPage() {
      this.goToPage(this.$store.getters.page + 1)
    },
    prevPage() {
      this.goToPage(this.$store.getters.page - 1)
    },
    goToPage: function (page) {
      /* Update URL hash to show the requested search result page. */
      this.$store.commit('page', page);

      // calculate query string from search fields and pagination variables
      const query = {
        page: this.$store.getters.page + 1
      };
      if (this.$store.getters.cursors[this.$store.getters.page])
        query.cursor = this.$store.getters.cursors[this.$store.getters.page];
      for (const field of this.$store.getters.fields)
        if (field.value)
          query[field.name] = field.value;

      if (this.$store.getters.sort_field['value']) {
        query[this.$store.getters.sort_field['name']] = this.$store.getters.sort_field['value'];
      }

      // push new route
      this.$router.push({
        name: 'endpoint',
        params: {endpoint: this.$store.getters.endpoint},
        query: query,
      });
    },

    getResultsPage() {
      /*
        This actually performs the search, and it puts the cursors and results in their respective arrays

        Side Effects:
          - Enables and disables the loading screen overlay
          - Retrieves an API page, updates the current page's entry in the this.$store.results
          - Gets the current and previous cursors with output from getCursorFromUrl using the next page url,
            and previous page url and updates this.$store.cursors if necessary
          - Updates error messages for forms or fields
       */
      // if we haven't changed the endpoint
      // and we already have the page in cache, return immediately
      if (this.$store.getters.results[this.$store.getters.page]) {
        return Promise.resolve();
      }
      this.updateQueryURL();
      this.$store.getters.search_error = "";
      this.$store.getters.field_errors = {};
      // Track current fetch operation, so we can throw away results if a fetch comes back after a new one has been
      // submitted by the user.
      const currentFetchID = Math.random();
      this.$store.commit('currentFetchID', currentFetchID);
      return fetch(this.$store.getters.query_url)
          .then((response) => {
            if (currentFetchID !== this.$store.getters.currentFetchID) {
              throw "canceled"
            }
            if (!response.ok) {
              throw response
            }
            return response.json();
          })
          .then((results_json) => {
            this.$store.commit('hitcount', results_json.count);

            // extract cursors
            let next_page_url = results_json.next;
            let prev_page_url = results_json.previous;
            if (this.$store.getters.page > 1 && !this.$store.getters.cursors[this.$store.getters.page - 1] && prev_page_url)
              this.$store.cursors[this.$store.getters.page - 1] = this.getCursorFromUrl(prev_page_url);
            if (!this.$store.getters.cursors[this.$store.getters.page + 1] && next_page_url)
              this.$store.cursors[this.$store.getters.page + 1] = this.getCursorFromUrl(next_page_url);

            // use this.$set to set array value with reactivity -- see https://vuejs.org/v2/guide/list.html#Caveats
            this.$set(this.$store.results, this.$store.page, results_json.results);
            this.$store.commit('resultsType', this.$store.getters.endpoint);
            this.$store.commit('showLoading', false);
          })
          .catch((response) => {
            if (response === "canceled") {
              return;
            }

            // scroll up to show error message
            this.$store.commit('showLoading', false);
            this.scrollToSearchForm();

            if (response.status === 400 && this.$store.getters.field_errors) {
              // handle field errors
              return response.json().then((object) => {
                this.$store.getters.field_errors = object;
                throw response;
              });
            }

            if (response.status) {
              // handle non-field API errors
              this.$store.getters.search_error = "Search error: API returned " +
                  response.status + " for the query " + this.$store.getters.query_url;
            } else {
              // handle connection errors
              this.$store.getters.search_error = "Search error: failed to load results from " + this.$store.getters.query_url;
            }

            console.log("Search error:", response);  // eslint-disable-line
            throw response;  // in case callers want to do further error handling
          }).catch(() => {
          });

    },
    resetResults: function () {
      /*
       Resets the search variables

       Side Effects:
         - 'resets' the following variables.
      */
      this.$store.commit('hitcount', null);
      this.$store.commit('page', 0);
      this.$store.commit('results', []);
      this.$store.commit('first_result_number', null);
      this.$store.commit('last_result_number', null);
      this.$store.commit('cursors', []);
      this.$store.commit('last_page', true);
      this.$store.commit('first_page', true);
    },
    seeCases: function (parameter, value) {
      /*
       A user has a "see cases" button on search hits in non-case endpoints, which starts a new case search
       filtering for the specified jurisdiction/etc.

       Side Effects:
       - Set URL hash for new search
       */
      this.$router.push({
        name: 'endpoint',
        params: {endpoint: 'cases'},
        query: {[parameter]: value, page: 1},
      });
    },
    getCursorFromUrl: function (url) {
      /* Extracts and returns cursor from given url. Return null if url is malformed or doesn't contain a cursor. */
      try {
        return new URL(url).searchParams.get("cursor");
      } catch {
        return null;
      }
    },

    scrollToResults() {
      this.scrollTo('#results_count_focus')
    },
    scrollToSearchForm() {
      this.scrollTo('#form-errors-heading')
    },
    scrollTo: function (selector) {
      /* Scroll to first element with target selector. */
      // use setTimeout to make sure element exists -- it may not have appeared yet if we just changed template vars
      setTimeout(() => {
        const el = document.querySelector(selector);
        el.focus({preventScroll: true}); // set focus for screenreaders
        el.scrollIntoView({behavior: "smooth", block: "nearest", inline: "start"});
      });
    },

    assembleUrl: function (page_size) {
      /* assembles and returns URL */
      const params = {}
      if (page_size) {
        params.page_size = page_size
      } else {
        params.page_size = this.$store.getters.page_size
      }


      if (this.$store.getters.cursors[this.$store.getters.page]) {
        params.cursor = this.$store.getters.cursors[this.$store.getters.page];
      }

      // build the query parameters using the form fields
      this.$store.getters.fields.forEach((field) => {
        if (field['value']) {
          params[field['name']] = field['value'];
        }
      });
      if (this.$store.getters.sort_field['value']) {
        params[this.$store.getters.sort_field['name']] = this.$store.getters.sort_field['value'];
      }

      return `${this.$store.getters.urls.api_root}${this.$store.getters.endpoint}/?${encodeQueryData(params)}`;
    },
    updateQueryURL: function () {
      this.$store.getters.query_url = this.assembleUrl();
    },
  },
}
</script>