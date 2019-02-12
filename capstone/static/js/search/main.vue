<template>
  <div class="search-page">
    <search-form ref="searchform"
                 v-on:new-search="newSearch"
                 class="bg-tan"
                 :field_errors="field_errors"
                 :search_error="search_error"
                 :choices="choices"
                 :docs_url="docs_url"
                 :scope_url="scope_url">
    </search-form>
    <a id="results_list"></a>
    <result-list v-on:see-cases="seeCases"
                 v-on:next-page="nextPage"
                 v-on:prev-page="prevPage"
                 :last_page="last_page"
                 :first_page="first_page"
                 :page="page"
                 :results="results"
                 :endpoint="endpoint"
                 :hitcount="hitcount"
                 :metadata_view_url_template="metadata_view_url_template"
                 :case_view_url_template="case_view_url_template">
    </result-list>
  </div>
</template>


<script>
  import SearchForm from './search-form.vue'
  import ResultList from './result-list.vue'

  export default {
    beforeMount: function () {
      /*
        Here we get a number of variables defined in the django template
       */
      // eslint-disable-next-line
      this.docs_url = docs_url;
      // eslint-disable-next-line
      this.scope_url = scope_url;
      // eslint-disable-next-line
      this.case_view_url_template = case_view_url_template;
      // eslint-disable-next-line
      this.metadata_view_url_template = metadata_view_url_template;
      // eslint-disable-next-line
      this.search_url = search_url;
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
        cursors: [],
        endpoint: 'cases', // only used in the title in search.html. The working endpoint is in the searchform component
        page_size: 10,
        choices: {},
        case_view_url_template: null,
        search_url: null,
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
          this.updateUrlHash();
        }

        // nextPage actually triggers the search
        this.nextPage(true);
      },

      nextPage: function (new_search = false) {
        /*
          Gets the next (or first) page of results. If we've already loaded it, we pull it from memory
          rather than getting it from the API twice

          Side Effects:
            - Updates URL hash with output from generateUrlHash()
            - Sets last page/first page flags via lastFirstCheck()
            - Changes the results page, which will change the list of visible cases in result-list
            - Gets 1 page of API results (and therefore changes lots of other stuff) with getResultsPage()
         */
        if (new_search) {
          let self = this;
          let url = this.assembleUrl(this.search_url, this.endpoint,
              this.cursors[this.page], this.page_size, this.$refs.searchform.fields);
          this.getResultsPage(url).then(self.lastFirstCheck);
        } else if (this.results[this.page + 1]) {
          this.page++;
          this.updateUrlHash();
          this.lastFirstCheck();
          this.scrollToResults();
        } else if (this.cursors[this.page + 1]) {
          this.page++;
          let self = this;
          let url = this.assembleUrl(this.search_url, this.endpoint, this.cursors[this.page],
              this.page_size, this.$refs.searchform.fields);
          this.getResultsPage(url).then(function () {
              self.updateUrlHash();
              self.lastFirstCheck();
              self.scrollToResults();
          });
        }
      },
      prevPage: function () {
        /*
          Gets the previous page of results. If we've already loaded it, we pull it from memory
          rather than getting it from the API twice

          Side Effects:
            - Updates URL hash via updateUrlHash()
            - Sets last page/first page flags via lastFirstCheck()
            - Changes the results page, which will change the list of visible cases in result-list
            - Gets 1 page of results (and therefore changes lots of other stuff) with getResultsPage()
         */
        //
        if (this.results[this.page - 1]) {
          this.page--;
          this.updateUrlHash()
          this.lastFirstCheck();
        } else if (this.cursors[this.page - 1]) {
          this.page--;
          let url = this.assembleUrl(this.search_url, this.endpoint, this.cursors[this.page],
              this.page_size, this.$refs.searchform.fields);
          let self = this;
          this.getResultsPage(url).then(function () {
            self.updateUrlHash()
            self.lastFirstCheck();
          });
        }
        this.scrollToResults();
      },
      lastFirstCheck: function () {
        /*
          This just checks to see if it's the last or first set of results, and sets two flags accordingly.
          I tried using a computed variable for this, but it never seemed to be updated when I needed it.

          Side Effects:
            - just sets the last_page and first_page flags, which are used to determine prev/next button status

         */
        this.last_page = !this.cursors[this.page + 1];

        this.first_page = this.page === 0;

      },
      getResultsPage: function (query_url) {
        /*
          This actually performs the search, and it puts the cursors and results in their respective arrays

          Side Effects:
            - Enables and disables the loading screen overlay
            - Retrieves an API page, updates the current page's entry in the this.results
            - Gets the current and previous cursors with output from getCursorFromUrl using the next page url,
              and previous page url and updates this.cursors if necessary
            - Updates error messages for forms or fields
         */
        this.search_error = "";
        this.field_errors = {};
        let self = this;
        this.startLoading();
        return fetch(query_url)
            .then(function (response) {
              if (!response.ok) { throw response }
              return response.json();
            })
            .then(function (results_json) {
              self.hitcount = results_json.count;
              let next_page_url = results_json.next;
              let prev_page_url = results_json.previous;

              if (!self.cursors[self.page]) {
                self.cursors[self.page] = self.getCursorFromUrl(query_url);
              }

              if (!self.cursors[self.page - 1] && prev_page_url) {
                self.cursors[self.page - 1] = self.getCursorFromUrl(prev_page_url);
              }

              if (!self.cursors[self.page + 1] && next_page_url) {
                self.cursors[self.page + 1] = self.getCursorFromUrl(next_page_url);
              }

              self.results[self.page] = results_json.results;
            })
            .catch(function (response){
              if (response.status === 400 &&  self.field_errors) {
                // handle field errors
                return response.json().then(function(object) {
                  self.field_errors = object;
                });
              } else if (response.status) {
                // handle non-field API errors
                self.search_error = "Search error: API returned " +
                response.status + " for the query " + query_url;
              } else {
                // handle connection errors
                self.search_error = "Search error: failed to load results from " + query_url;
              }
            })
            .then(function () {
              self.stopLoading();
            })
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
        this.cursors = [];
        this.last_page = true;
        this.first_page = true;
      },
      startLoading: function () {
        /* shows the loading screen and throbber */
        document.getElementById("loading-overlay").style.display = 'block';
      },
      stopLoading: function () {
        /* hides the loading screen and throbber */
        document.getElementById("loading-overlay").style.display = 'none';
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
          new_field['value'] = val;
          arr.push(new_field);
          return arr;
        }, []);
      },
      generateUrlHash: function (endpoint, cursors, page, page_size, fields) {
        /* returns new URL hash */
        let params;
        if (cursors[page]) {
          params = {
            'page': page + 1,
            'cursor': cursors[page],
            'page_size': page_size
          }
        } else {
          params = {
            'page': page + 1,
            'page_size': page_size
          }
        }
        let param_string = Object.keys(params).reduce(function (str, param_name) {
          return str + param_name + ":" + params[param_name] + "/"
        }, '');

        let filters_string = fields.reduce(function (string_accumulator, chunk) {
          string_accumulator += encodeURIComponent(chunk['name']) + ":" + encodeURIComponent(chunk['value']) + "/";
          return string_accumulator;
        }, '');

        let new_url_hash = "#" + endpoint + "/" + param_string + "filters/" + filters_string;
        return new_url_hash;

      },
      getCursorFromUrl: function (url) {
        /* extracts and returns cursor from given url */
        if (!url || !url.includes('cursor=')) {
          return;
        }
        return url.split('cursor=')[1].split('&')[0];
      },
      scrollToResults: function() {
          /* scrolls to the results area */
          let elmnt = document.getElementById("results_list");
          elmnt.scrollIntoView();
      },
      assembleUrl: function (search_url, endpoint, cursor = null, page_size, fields) {
        /* assembles and returns URL */

        let query_url = search_url + endpoint + "/?";

        if (cursor) {
          query_url += "cursor=" + cursor + "&";
        }

        // build the query parameters using the form fields
        if (fields.length > 0) {
          for (let i = fields.length - 1; i >= 0; i--) {
            let value = fields[i]['value'];
            if (value == undefined || value == null) {
              value='';
            }
            query_url += (fields[i]['name'] + "=" + value + "&");
          }
        }
        query_url += "page_size=" + page_size;
        return query_url;
      }
    }
  }
</script>
