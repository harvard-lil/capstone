<template>
  <div class="search-page">
    <div class="row">
      <search-form ref="searchform"
                   v-on:new-search="newSearch"
                   :class="searchFormClass"
                   :field_errors="field_errors"
                   :search_error="search_error"
                   :showLoading="showLoading"
                   :endpoint.sync="endpoint"
                   :urls="urls"
                   :choices="choices">
      </search-form>
      <result-list v-on:see-cases="seeCases"
                   v-on:next-page="nextPage"
                   v-on:prev-page="prevPage"
                   :class="searchResultsClass"
                   :last_page="last_page"
                   :first_page="first_page"
                   :page="page"
                   :results="results"
                   :resultsType="resultsType"
                   :resultsShown="resultsShown"
                   :first_result_number="first_result_number"
                   :last_result_number="last_result_number"
                   :showLoading="showLoading"
                   :endpoint="endpoint"
                   :hitcount="hitcount"
                   :urls="urls">
      </result-list>
    </div>
  </div>
</template>


<script>
import SearchForm from './search-form.vue'
import ResultList from './result-list.vue'
import {encodeQueryData} from '../utils'

export default {
  beforeMount: function () {
    /*
      Here we get a number of variables defined in the django template
     */
    this.urls = urls;  // eslint-disable-line
    this.choices = choices;  // eslint-disable-line
  },
  mounted: function () {
    /* Read url state when first loaded. */
    this.$route ? this.handleRouteUpdate(this.$route) : this.updateSearchFormFields();
  },
  watch: {
    /* Read url state on change. */
    '$route': function (route, oldRoute) {
      this.handleRouteUpdate(route, oldRoute);
    },
    results() {
      if (this.results.length && !this.resultsShown) {
        this.resultsShown = true
      }
    },
    resultsShown() {
      let fullWidth = "col-md-12";
      this.searchFormClass = this.results.length ? "col-md-4" : fullWidth;
      this.searchResultsClass = this.results.length ? "col-md-8" : fullWidth;
    },
  },
  components: {SearchForm, ResultList},
  data: function () {
    return {
      title: "Search",
      hitcount: null,
      page: 0,
      results: [],
      resultsType: '',
      resultsShown: false,
      first_result_number: null,
      last_result_number: null,
      showLoading: false,
      cursors: [],
      endpoint: 'cases',
      page_size: 10,
      choices: {},
      cursor: null,
      last_page: true,
      first_page: true,
      field_errors: {},
      search_error: null,
      searchFormClass: '',
      searchResultsClass: '',
    }
  },
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
      return route.params.endpoint + '|' + queryKeys.map(key => `${key}:${query[key]}`).join('|');
    },
    updateSearchFormFields(query) {
      const searchform = this.$refs.searchform;
        // load search fields and values from query params
        let fields = searchform.endpoints[this.endpoint];
        fields.forEach((field) => {
          if (field && query[field.name]) {
            field.value = query[field.name];
            fields[field] = field;
          }
        })
        searchform.fields = fields;
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
          this.endpoint = route.params.endpoint;
        }
        this.updateSearchFormFields(query);
        this.resetResults();
      }


      // handle page=n parameter: if it is 1 or greater, we show the requested search result page
      const newPage = query.page ? parseInt(query.page) - 1 : undefined;
      if (newPage >= 0) {
        this.page = newPage;
        if (query.cursor)
          this.cursors[this.page] = query.cursor;

        // render results if we have enough information to do so:
        if (this.page === 0 || this.results[this.page] || this.cursors[this.page]) {
          this.getResultsPage().then(() => {
            this.scrollToResults();

            // set variables for pagination display -- result count and back and next buttons
            this.last_page = !this.cursors[this.page + 1];
            this.first_page = this.page === 0;
            this.first_result_number = 1 + this.page_size * this.page;
            this.last_result_number = this.first_result_number + this.results[this.page].length - 1;
          });
        }
      }
    },
    newSearch() {
      this.goToPage(0)
    },
    nextPage() {
      this.goToPage(this.page + 1)
    },
    prevPage() {
      this.goToPage(this.page - 1)
    },
    goToPage: function (page) {
      /* Update URL hash to show the requested search result page. */
      this.page = page;

      // calculate query string from search fields and pagination variables
      const query = {
        page: this.page + 1
      };
      if (this.cursors[this.page])
        query.cursor = this.cursors[this.page];
      for (const field of this.$refs.searchform.fields)
        if (field.value)
          query[field.name] = field.value;

      // push new route
      this.$router.push({
        name: 'endpoint',
        params: {endpoint: this.endpoint},
        query: query,
      });
    },

    getResultsPage() {
      /*
        This actually performs the search, and it puts the cursors and results in their respective arrays

        Side Effects:
          - Enables and disables the loading screen overlay
          - Retrieves an API page, updates the current page's entry in the this.results
          - Gets the current and previous cursors with output from getCursorFromUrl using the next page url,
            and previous page url and updates this.cursors if necessary
          - Updates error messages for forms or fields
       */
      // if we haven't changed the endpoint
      // and we already have the page in cache, return immediately
      if (this.results[this.page]) {
        return Promise.resolve();
      }

      const query_url = this.assembleUrl();
      this.search_error = "";
      this.field_errors = {};
      // Track current fetch operation, so we can throw away results if a fetch comes back after a new one has been
      // submitted by the user.
      const currentFetchID = Math.random();
      this.currentFetchID = currentFetchID;
      this.showLoading = true;
      return fetch(query_url)
          .then((response) => {
            if (currentFetchID !== this.currentFetchID) {
              throw "canceled"
            }
            if (!response.ok) {
              throw response
            }
            return response.json();
          })
          .then((results_json) => {
            this.hitcount = results_json.count;

            // extract cursors
            let next_page_url = results_json.next;
            let prev_page_url = results_json.previous;
            if (this.page > 1 && !this.cursors[this.page - 1] && prev_page_url)
              this.cursors[this.page - 1] = this.getCursorFromUrl(prev_page_url);
            if (!this.cursors[this.page + 1] && next_page_url)
              this.cursors[this.page + 1] = this.getCursorFromUrl(next_page_url);

            // use this.$set to set array value with reactivity -- see https://vuejs.org/v2/guide/list.html#Caveats
            this.$set(this.results, this.page, results_json.results);
            this.resultsType = this.endpoint;
            this.showLoading = false;
          })
          .catch((response) => {
            if (response === "canceled") {
              return;
            }

            // scroll up to show error message
            this.showLoading = false;
            this.scrollToSearchForm();

            if (response.status === 400 && this.field_errors) {
              // handle field errors
              return response.json().then((object) => {
                this.field_errors = object;
                throw response;
              });
            }

            if (response.status) {
              // handle non-field API errors
              this.search_error = "Search error: API returned " +
                  response.status + " for the query " + query_url;
            } else {
              // handle connection errors
              this.search_error = "Search error: failed to load results from " + query_url;
            }

            console.log("Search error:", response);  // eslint-disable-line
            throw response;  // in case callers want to do further error handling
          }).catch(()=>{});

    },
    resetResults: function () {
      /*
       Resets the search variables

       Side Effects:
         - 'resets' the following variables.
      */
      this.title = "Search";
      this.hitcount = null;
      this.page = 0;
      this.results = [];
      this.first_result_number = null;
      this.last_result_number = null;
      this.cursors = [];
      this.last_page = true;
      this.first_page = true;
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

    assembleUrl: function () {
      /* assembles and returns URL */
      const params = {
        page_size: this.page_size,
      };
      if (this.cursors[this.page]) {
        params.cursor = this.cursors[this.page];
      }

      // build the query parameters using the form fields
      this.$refs.searchform.fields.forEach((field) => {
        if (field['value']) {
          params[field['name']] = field['value'];
        }
      });

      return `${this.urls.api_root}${this.endpoint}/?${encodeQueryData(params)}`;
    }
  }
}
</script>