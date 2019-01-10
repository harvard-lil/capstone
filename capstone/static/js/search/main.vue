<template>
  <div>

    <search-form ref="searchform" v-on:change-endpoint="resetForm" v-on:new-search="newSearch"
                 :choice_source="choice_source"></search-form>
    <result-list v-on:see-cases="seeCases" v-on:next-page="nextPage"
                 v-on:prev-page="prevPage" :last_page="last_page" :first_page="first_page" :page="page"
                 :results="results" :endpoint="endpoint" :hitcount="hitcount"
                 :case_view_url_template="case_view_url_template"></result-list>
  </div>
</template>


<script>
    import SearchForm from './search-form.vue'
    import ResultList from './result-list.vue'
    export default
    {
        beforeMount: function () {
            // eslint-disable-next-line
            this.choice_source = choice_source;
            // eslint-disable-next-line
            this.case_view_url_template = case_view_url_template;
            // eslint-disable-next-line
            this.search_url = search_url;
            // eslint-disable-next-line
            this.bullet_url = bullet_url;
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
                endpoint: 'cases', // only used in the title in search.html. The working endpoint is in the searchform component
                page_size: 10,
                last_page: true,
                first_page: true,
                choices: {},
                choice_source: null,
                case_view_url_template: null,
                search_url: null
            }
        },
        methods: {
            // Each time a new search is queued up
            newSearch: function (fields, endpoint) {
                // use all the fields and endpoint to build the query url
                this.endpoint = endpoint;
                this.resetForm();
                var query_url = this.search_url + endpoint + "/?";
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
                this.first_page = true;
                this.next_page_url = query_url;
                this.nextPage();
            },
            nextPage: function () {
                let self = this;
                if (this.results[this.page + 1]) {
                    this.page++;
                    this.pageCheck()
                } else if (this.next_page_url) {
                    this.getResultsPage(this.next_page_url).then(function () {
                        self.pageCheck();
                    });
                }
            },
            prevPage: function () {
                if (this.page > 0) {
                    this.page--;
                    this.pageCheck();
                }
            },
            getResultsPage: function (query_url) {
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
                        //console.log(response.status, response.statusText, query_url)
                    })
                    .then(function (results_json) {
                        self.hitcount = results_json.count;
                        self.next_page_url = results_json.next;
                        self.prev_page_url = results_json.previous;
                        self.page = self.results.push(results_json.results) - 1;
                    })
                    .then(function () {
                        self.stopLoading();
                    })

            },
            resetForm: function () {
                this.title = "Search"
                this.hitcount = null;
                this.next_page_url = null;
                this.prev_page_url = null;
                this.page = 0;
                this.results = [];
                this.last_page = true;
                this.first_page = true;
            },
            pageCheck: function () {
                if (this.prev_page_url === null || this.page === 0) {
                    this.first_page = true
                } else {
                    this.first_page = false
                }

                if (this.next_page_url === null && this.page === this.results.length - 1) {
                    this.last_page = true
                } else {
                    this.last_page = false
                }
            },
            startLoading: function () {
                document.getElementById("loading-overlay").style.display = 'block';
            },
            stopLoading: function () {
                document.getElementById("loading-overlay").style.display = 'none';
            },
            seeCases: function (parameter, value) {
                let fields = [{"label": parameter, "name": parameter, "value": value}]
                this.newSearch(fields, "cases")
                this.$refs.searchform.changeEndpoint("cases", fields)
            }
        },
        delimiters: ['[[', ']]'],
        template: '',
    }
</script>
