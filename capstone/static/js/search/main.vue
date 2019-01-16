<template>
  <div>

    <search-form ref="searchform" v-on:change-endpoint="resetResults" v-on:new-search="newSearch"
                 :choices="choices"></search-form>
    <result-list v-on:see-cases="seeCases" v-on:next-page="nextPage"
                 v-on:prev-page="prevPage" :last_page="last_page" :first_page="first_page" :page="page"
                 :results="results" :endpoint="endpoint" :hitcount="hitcount"
                 :case_view_url_template="case_view_url_template"></result-list>
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
            this.case_view_url_template = case_view_url_template;
            // eslint-disable-next-line
            this.search_url = search_url;
            // eslint-disable-next-line
            this.choices = choices;
        },
        mounted: function() {
            if (window.location.hash) {
                /*
                    Here we're processing the info in the URL parameters
                 */
                let hash = window.location.hash.substr(1);
                let endpoint = this.getHashEndpoint(hash);
                let fields = this.getHashFilterFields(hash);
                let params = this.getHashParams(hash);
                if (params.hasOwnProperty("page")) {
                    this.page = params['page'] -1;
                }
                if (params.hasOwnProperty("cursor")) {
                    this.cursors[this.page] = params['cursor'];
                }
                if (params.hasOwnProperty("page_size")) {
                    this.page_size = params['page_size'];
                }
                if (this.$refs.searchform.endpoint != endpoint) {
                    this.$refs.searchform.changeEndpoint(endpoint, fields);
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
                next_page_url: null,
                prev_page_url: null,
                page: 0,
                results: [],
                cursors: [],
                endpoint: 'cases', // only used in the title in search.html. The working endpoint is in the searchform component
                page_size: 1,
                choices: {},
                case_view_url_template: null,
                search_url: null,
                cursor: null,
                last_page: true,
                first_page: true
            }
        },

        methods: {
            // Each time a new search is queued up
            newSearch: function (fields, endpoint, loaded_from_url=false) {
                // use all the fields and endpoint to build the query url
                this.endpoint = endpoint;
                var query_url = this.search_url + endpoint + "/?";

                // if we have a cursor specified in the URL, add that to the request
                if (loaded_from_url && this.cursors[this.page]) {
                    query_url += "cursor=" + this.cursors[this.page] + "&";
                } else {
                    this.resetResults();
                }

                // build the query parameters using the form fields
                if (fields.length > 0) {
                    for (var i = fields.length - 1; i >= 0; i--) {
                        if (i !== fields.length - 1) {
                            query_url += "&";
                        }
                        if (fields[i]['value']) {
                            query_url += (fields[i]['name'] + "=" + fields[i]['value']);
                        }
                    }
                    query_url += "&page_size=" + this.page_size;
                } else {
                    query_url += "page_size=" + this.page_size;
                }

                // nextPage actually triggers the search
                this.next_page_url = query_url;
                this.nextPage(true);
            },
            nextPage: function (new_search=false) {
                /*
                  Gets the next (or first) page of results. If we've already loaded it, we pull it from memory
                  rather than getting it from the API twice
                 */
                if (new_search) {
                    let self = this;
                    this.getResultsPage(this.next_page_url).then(function () {
                        self.updateUrlHash();
                        self.lastFirstCheck();
                    });
                } else if (this.results[this.page + 1]) {
                    this.page++;
                    this.updateUrlHash();
                    this.lastFirstCheck();
                }  else if (this.cursors[this.page + 1]) {
                    this.page++;
                    let self = this;
                    this.getResultsPage(this.next_page_url).then(function () {
                        self.updateUrlHash();
                        self.lastFirstCheck();
                    });
                }

            },
            prevPage: function () {
                /*
                  Gets the previous page of results. If we've already loaded it, we pull it from memory
                  rather than getting it from the API twice
                 */
                if (this.results[this.page - 1]) {
                    this.page--;
                    this.updateUrlHash();
                    this.lastFirstCheck();
                } else if (this.cursors[this.page - 1]) {
                    this.page--;
                    let self = this;
                    this.getResultsPage(this.prev_page_url, "prev").then(function () {
                        self.updateUrlHash();
                        self.lastFirstCheck();
                    });
                }
            },
            lastFirstCheck: function() {
                /*
                  This just checks to see if it's the last or first set of results, and sets two flags accordingly.
                  I tried using a computed variable for this, but it never seemed to be updated when I needed it.
                 */
              if (this.cursors[this.page + 1]) {
                  this.last_page = false;
              } else {
                  this.last_page = true;
              }

              if (this.page == 0){
                  this.first_page = true;
              } else {
                  this.first_page = false;
              }

            },
            getResultsPage: function (query_url) {
                /*
                  This actually performs the search, and it puts the cursors and results in their respective arrays
                 */
                let self = this;
                this.startLoading();
                return fetch(query_url)
                    .then(function (response) {
                        if (response.ok) {
                            return response.json();
                        }
                        if (response.status === 500) {
                            document.getElementById("loading-overlay").style.display = 'none';
                            //TODO
                        }
                    })
                    .then(function (results_json) {
                        self.hitcount = results_json.count;
                        self.next_page_url = results_json.next;
                        self.prev_page_url = results_json.previous;

                        if (!self.cursors[self.page]) {
                            self.cursors[self.page] = self.getCursorFromUrl(query_url);
                        }

                        if (!self.cursors[self.page - 1] && self.prev_page_url) {
                            self.cursors[self.page - 1] = self.getCursorFromUrl(self.prev_page_url);
                        }

                        if (!self.cursors[self.page + 1] && self.next_page_url) {
                            self.cursors[self.page + 1] = self.getCursorFromUrl(self.next_page_url);
                        }

                        self.results[self.page] = results_json.results;

                    })
                    .then(function () {
                        self.stopLoading();
                    })
            },
            resetResults: function () {
                this.title = "Search"
                this.hitcount = null;
                this.next_page_url = null;
                this.prev_page_url = null;
                this.page = 0;
                this.results = [];
                this.cursors = [];
                this.last_page= true;
                this.first_page= true;
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
                 filtering for the specified court/etc.
                 */
                //document.getElementById("loading-overlay").style.display = 'none';
                let fields = [{"label": parameter, "name": parameter, "value": value}]
                this.newSearch(fields, "cases")
                this.$refs.searchform.changeEndpoint("cases", fields);
            },
            getHashEndpoint: function (hash) {
                if (!hasOwnProperty.call(this.$refs.searchform.endpoints, hash.split('filters')[0].split("/")[0])) {
                    return;
                }
                return hash.split('filters')[0].split("/")[0];
            },
            getHashParams: function (hash) {
                let param_chunks = hash.split("filters")[0].split('/');

                return param_chunks.reduce(function (obj, chunk) {
                    if (!chunk.includes(':')) {
                        return obj;
                    }
                    let [prm, val] = chunk.split(':')
                    obj[prm] = val;
                    return obj;
                }, {});
            },
            getHashFilterFields: function (hash) {
                let filters = hash.split("filters")[1].split('/');
                let searchform = this.$refs.searchform;
                return filters.reduce(function (arr, chunk) {
                    if (!chunk.includes(':')) {
                        return arr;
                    }
                    let [fld, val] = chunk.split(':');
                    let new_field = searchform.getFieldEntry(fld, searchform.endpoint)
                    if (!new_field) {
                        return arr;
                    }
                    new_field['value'] = val;
                    arr.push(new_field);
                    return arr;
                }, []);
            },
            updateUrlHash: function () {
                /*
                  updates the URL based on the fields/endpoint/etc
                 */
                let params;
                if (this.cursors[this.page]) {
                  params = {
                      'page': this.page + 1,
                      'cursor': this.cursors[this.page],
                      'page_size': this.page_size
                  }
                } else {
                  params = {
                      'page': this.page + 1,
                      'page_size': this.page_size
                  }
                }
                let param_string = Object.keys(params).reduce(function (str, param_name) {
                    return str + param_name + ":" + params[param_name] + "/"
                }, '');

                let filters_string = this.$refs.searchform.fields.reduce(function (string_accumulator, chunk) {
                    string_accumulator += encodeURIComponent(chunk['name']) + ":" + encodeURIComponent(chunk['value']) + "/";
                    return string_accumulator;
                }, '');

                let new_url_hash = "#" + this.endpoint + "/" + param_string + "filters/" + filters_string;
                window.location.hash = new_url_hash;
            },
            getCursorFromUrl: function (url) {
                if (!url || !url.includes('cursor=')) {
                    return;
                }
                return url.split('cursor=')[1].split('&')[0];
            }
        }
    }
</script>
