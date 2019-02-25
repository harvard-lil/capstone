<template>
  <div class="search-page">
    <search-form ref="searchform"
                 v-on:new-search="newSearch"
                 class="bg-tan"
                 :field_errors="field_errors"
                 :search_error="search_error"
                 :urls="urls"
                 :choices="choices">
    </search-form>
    <a id="results_list"></a>
    <result-list v-on:see-cases="seeCases"
                 v-on:next-page="nextPage"
                 v-on:prev-page="prevPage"
                 :last_page="last_page"
                 :first_page="first_page"
                 :page="page"
                 :results="results"
                 :first_result_number="first_result_number"
                 :last_result_number="last_result_number"
                 :show_loading="show_loading"
                 :endpoint="endpoint"
                 :hitcount="hitcount"
                 :urls="urls">
    </result-list>
  </div>
</template>


<script>
  import SearchForm from './search-form.vue'
  import ResultList from './result-list.vue'
  import * as VueScrollTo from 'vue-scrollto'
  import 'url-polyfill'  // can be removed when core-js upgraded to 3.0

  export default {
    beforeMount: function () {
      /*
        Here we get a number of variables defined in the django template
       */
      // eslint-disable-next-line
      this.urls = urls;
      // eslint-disable-next-line
      this.choices = choices;
    },
    mounted: function () {
      if (window.location.hash) {
        /*
            Here we're processing the info in the URL parameters
         */
        let hash = window.location.hash.substr(1);
        let endpoint = this.getHashEndpoint(hash);
        let fields = this.getHashFilterFields(hash);
        let params = this.getHashParams(hash);
        if (params.hasOwnProperty("page")) {
          this.page = params['page'] - 1;
        }
        if (params.hasOwnProperty("cursor")) {
          this.cursors[this.page] = params['cursor'];
        }
        if (params.hasOwnProperty("page_size")) {
          this.page_size = params['page_size'];
        }
        if (this.$refs.searchform.endpoint !== endpoint) {
             // eslint-disable-next-line
          console.log("needing to pass in , fields", fields)
          this.$refs.searchform.endpoint = endpoint;
        }

        this.newSearch(fields, endpoint, true);
      }

    },
    components: {
      'search-form': SearchForm,
      'result-list': ResultList
    },
    data: function () {
      return {
        title: "Search",
        hitcount: null,
        page: 0,
        results: [],
        first_result_number: null,
        last_result_number: null,
        show_loading: false,
        cursors: [],
        endpoint: 'cases', // only used in the title in search.html. The working endpoint is in the searchform component
        page_size: 10,
        choices: {},
        cursor: null,
        last_page: true,
        first_page: true,
        field_errors: {},
        search_error: null
      }
    },
    methods: {
      newSearch: function (fields, endpoint, loaded_from_url = false) {
        /*
         Sets us up for a new search.

         Side Effects:
           - Sets the correct endpoint and changes the visible fields
           - Resets any existing results via resetResults()
           - Calls triggers the actual search via nextPage()
        */

        if (this.$refs.searchform.fields != fields && fields.length > 0) {
          this.$refs.searchform.replaceFields(fields);
        }
        this.endpoint = endpoint;
        if (!loaded_from_url) {
          this.resetResults();
        }
        this.goToPage(this.page);
      },

      nextPage() { this.goToPage(this.page + 1) },
      prevPage() { this.goToPage(this.page - 1) },
      goToPage: function(page) {
        /*
          Gets the given page of results. If we've already loaded it, we pull it from memory
          rather than getting it from the API twice

          Side Effects:
            - Updates URL hash via updateUrlHash()
            - Sets last page/first page flags
            - Changes the results page, which will change the list of visible cases in result-list
            - Gets 1 page of results (and therefore changes lots of other stuff) with getResultsPage()
         */
        // we can load the requested page if it is the first page, or we have results cached, or we have a cursor cached
        if (page === 0 || this.results[page] || this.cursors[page]) {
          this.page = page;
          this.updateUrlHash();
          this.getResultsPage().then(()=>{
            // set variables for pagination display -- result count and back and next buttons
            this.last_page = !this.cursors[this.page + 1];
            this.first_page = this.page === 0;
            this.first_result_number = 1 + this.page_size * this.page;
            this.last_result_number = this.first_result_number + this.results[this.page].length - 1;
          });
        }
      },
      getResultsPage: function () {
        /*
          This actually performs the search, and it puts the cursors and results in their respective arrays

          Side Effects:
            - Enables and disables the loading screen overlay
            - Retrieves an API page, updates the current page's entry in the this.results
            - Gets the current and previous cursors with output from getCursorFromUrl using the next page url,
              and previous page url and updates this.cursors if necessary
            - Updates error messages for forms or fields
         */
        // if we already have the page in cache, return immediately
        if (this.results[this.page]){
          return Promise.resolve();
        }

        const query_url = this.assembleUrl();
        this.search_error = "";
        this.field_errors = {};
        // Track current fetch operation, so we can throw away results if a fetch comes back after a new one has been
        // submitted by the user.
        const currentFetchID = Math.random();
        this.currentFetchID = currentFetchID;
        this.startLoading();
        return fetch(query_url)
          .then((response)=>{
            if (currentFetchID !== this.currentFetchID) { throw "canceled" }
            if (!response.ok) { throw response }
            return response.json();
          })
          .then((results_json)=>{
            this.hitcount = results_json.count;
            let next_page_url = results_json.next;
            let prev_page_url = results_json.previous;

            if (!this.cursors[this.page]) {
              this.cursors[this.page] = this.getCursorFromUrl(query_url);
            }

            if (!this.cursors[this.page - 1] && prev_page_url) {
              this.cursors[this.page - 1] = this.getCursorFromUrl(prev_page_url);
            }

            if (!this.cursors[this.page + 1] && next_page_url) {
              this.cursors[this.page + 1] = this.getCursorFromUrl(next_page_url);
            }

            // use this.$set to set array value with reactivity -- see https://vuejs.org/v2/guide/list.html#Caveats
            this.$set(this.results, this.page, results_json.results);
            this.stopLoading();
          })
          .catch((response)=>{
            if (response === "canceled"){
              return;
            }

            // scroll up to show error message
            this.stopLoading();
            this.scrollToSearchForm();

            if (response.status === 400 && this.field_errors) {
              // handle field errors
              return response.json().then((object)=>{
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

            console.log("Search error:", response);
            throw response;  // in case callers want to do further error handling
          });

      },
      updateUrlHash: function () {
        /*
         Updates the URL with the value of component-scoped variables.

         Side Effects:
           - changes the URL hash
        */
        window.location.hash = this.generateUrlHash(
            this.endpoint,
            this.cursors,
            this.page,
            this.page_size,
            this.$refs.searchform.fields);
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
      startLoading: function () {
        /* shows the loading screen and throbber */
        this.scrollToResults();
        this.show_loading = true;
      },
      stopLoading: function () {
        /* hides the loading screen and throbber */
        this.show_loading = false;
      },
      seeCases: function (parameter, value) {
        /*
         A user has a "see cases" button on search hits in non-case endppints, which starts a new case search
         filtering for the specified jurisdiction/etc.

         Side Effects:
         - Resets the fields variable changes the endpoint, and starts a new search via newSearch()
         */
        let fields = [{"label": parameter, "name": parameter, "value": value}];
        this.newSearch(fields, "cases");
      },
      getHashEndpoint: function (hash) {
        /* Gets endpoint from URL hash, validating it against this.$refs.searchform.endpoints, */
        if (!hasOwnProperty.call(this.$refs.searchform.endpoints, hash.split('filters')[0].split("/")[0])) {
          return;
        }
        return hash.split('filters')[0].split("/")[0];
      },
      getHashParams: function (hash) {
        /* Gets the parameters (not including search terms/filters) from the URL hash */

        let param_chunks = hash.split("filters")[0].split('/');

        return param_chunks.reduce(function (obj, chunk) {
          if (!chunk.includes(':')) {
            return obj;
          }
          let [prm, val] = chunk.split(':');
          obj[prm] = val;
          return obj;
        }, {});
      },
      getHashFilterFields: function (hash) {
        /* Gets the search terms/filters from  URL hash, and gets field objects via searchform.getFieldEntry() */
        let filters = hash.split("filters")[1].split('/');
        let searchform = this.$refs.searchform;
        return filters.reduce(function (arr, chunk) {
          if (!chunk.includes(':')) {
            return arr;
          }
          let [fld, val] = chunk.split(':');
          let new_field = searchform.getFieldEntry(fld, searchform.endpoint);
          if (!new_field) {
            return arr;
          }
          new_field['value'] = decodeURIComponent(val);
          arr.push(new_field);
          return arr;
        }, []);
      },
      generateUrlHash: function (endpoint, cursors, page, page_size, fields) {
        /* returns new URL hash */
        let params = {
          'page': page + 1,
          'page_size': page_size
        };
        if (cursors[page])
          params.cursor = cursors[page];

        let param_string = Object.keys(params)
          .map(param_name => `${param_name}:${params[param_name]}/`)
          .join('');

        let filters_string = fields
          .filter(field => field['value'])  // remove fields with non-truthy value
          .map(field => `${encodeURIComponent(field['name'])}:${encodeURIComponent(field['value'])}/`)
          .join('');

        return `#${endpoint}/${param_string}filters/${filters_string}`;
      },
      getCursorFromUrl: function (url) {
        /* Extracts and returns cursor from given url. Return null if url is malformed or doesn't contain a cursor. */
        try {
          return new URL(url).searchParams.get("cursor");
        }catch{
          return null;
        }
      },

      scrollToResults() { this.scrollTo('#results_list') },
      scrollToSearchForm() { this.scrollTo('.search-page') },
      scrollTo: function(selector){
        /* Scroll to first element with target selector, taking into account offset for navbar. */
        VueScrollTo.scrollTo(document.querySelector(selector), 500, {
          offset: -document.getElementById('main-nav').offsetHeight
        });
      },

      encodeQueryData: function(data) {
        /* encodes data as a query parameter string */
        const searchParams = new URLSearchParams();
        Object.keys(data).forEach(key => searchParams.append(key, data[key]));
        return searchParams.toString();
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
        this.$refs.searchform.fields.forEach((field)=> {
          if (field['value']) {
            params[field['name']] = field['value'];
          }
        });

        return `${this.urls.api_root}${this.endpoint}/?${this.encodeQueryData(params)}`;
      }
    }
  }
</script>
