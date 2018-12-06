// This is essentially each endpoint with its API interface
const endpoint_list = {
    cases: [
        {
            name: "name_abbreviation",
            label: "Case Name Abbreviation",
            value: "",
            format: "e.g. Taylor v. Sprinkle",
            info: "the abbreviated case name"
        },
        {
            name: "decision_date_min",
            label: "Decision Date Earliest",
            format: "YYYY-MM-DD",
            info: "the earliest date on which your results could have been decided"
        },
        {
            name: "decision_date_max",
            value: "",
            label: "Decision Date Latest",
            format: "YYYY-MM-DD",
            info: "the latest date on which your results could have been decided"
        },
        {
            name: "docket_number",
            value: "",
            label: "Docket Number",
            format: "(string)",
            info: "the docket number assigned by the court"
        },
        {
            name: "citation",
            value: "",
            label: "Citation",
            format: "e.g. 1 Ill. 17",
            info: "the case citation"
        },
        {
            name: "reporter",
            value: "",
            label: "Reporter",
            format: "e.g. ill-app-ct",
            info: ""
        },
        {
            name: "court",
            value: "",
            label: "Court",
            format: "e.g. ill-app-ct",
            info: ""
        },
        {
            name: "jurisdiction",
            value: "",
            label: "Jurisdiction",
            choices: 'jurisdiction',
            format: "e.g. ill-app-ct",
            info: ""
        },
        {
            name: "search",
            value: "",
            label: "Full-Text Search",
            default: true,
            format: "e.g. \'insurance\'illinois",
            info: ""
        }
    ],
    courts: [
        {
            name: "slug",
            value: "",
            label: "Name",
            format: "e.g. ill-app-ct",
            info: "A slug is a unique alphanumeric identifier which is more readable than a numeric ID."
        },
        {
            name: "name",
            value: "",
            label: "Name",
            format: "e.g. \"Illinois Supreme Court\"",
            info: "the official full court name"
        },
        {
            name: "name_abbreviation",
            value: "",
            format: "e.g. \"Ill.\"",
            label: "Name Abbreviation",
            info: "the abbreviated court name"
        },
        {
            name: "jurisdiction",
            value: "",
            label: "Jurisdiction",
            choices: 'jurisdiction',
            default: true,
            info: "the court's jurisdiction"
        }
    ],
    jurisdictions: [
        {
            name: "id",
            value: "",
            format: "e.g. 47",
            label: "Database ID",
            info: "A slug is a unique string that represents a database entry which is more readable than a numeric ID."
        },
        {
            name: "name",
            value: "",
            label: "Name",
            format: "e.g. \"Ill.\"",
            info: "the short, official name of the jurisdiction"
        },
        {
            name: "name_long",
            value: "",
            label: "Long Name",
            format: "e.g. \"Illinois\"",
            default: true,
            info: "the long, official name of the jurisdiction"
        },
        {
            name: "whitelisted",
            value: "",
            label: "Whitelisted Jurisdiction",
            choices: 'whitelisted',
            info: "Whitelisted cases are not subject to the 500 case per day access limitation."
        }
    ],
    volumes: [],
    reporters: [
        {
            name: "full_name",
            value: "",
            label: "Full Name",
            format: "e.g. \"Illinois Appellate Court Reports\"",
            info: "the full reporter name"
        },
        {
            name: "short_name",
            value: "",
            label: "Short Name",
            format: "e.g. \"Ill. App.\"",
            info: "the short reporter name"
        },
        {
            name: "start_year",
            value: "",
            label: "Long Name",
            format: "e.g. \"1893\"",
            info: "the year in which the reporter began publishing"
        },
        {
            name: "end_year",
            value: "",
            label: "Long Name",
            format: "e.g. \"1894\"",
            info: "the year in which the reporter stopped publishing"
        },
        {
            name: "jurisdiction",
            value: "",
            label: "Jurisdiction",
            choices: 'jurisdiction',
            default: true,
            info: "the reporter's jurisdiction"
        }
    ]
};

// This is the main Vue app
var app = new Vue({
    el: '#app',
    data: {
        title: "Browse or Search",
        hitcount: null,
        next_page_url: null,
        prev_page_url: null,
        page: 0,
        results: [],
        api_url: search_url,
        endpoint: 'cases', // only used in the title in browse.html. The working endpoint is in the searchform component
        page_size: 10,
        last_page: true,
        first_page: true,
        choices: {}
    },
    methods: {
        // Each time a new search is queued up
        newSearch: function (fields, endpoint) {
            console.log(fields)
            // use all the fields and endpoint to build the query url
            this.endpoint = endpoint;
            this.resetForm();
            var query_url = this.api_url + endpoint + "/?";
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
            if (this.results[this.page + 1]) {
                this.page++;
                this.pageCheck()
            } else if (this.next_page_url) {
                this.getResultsPage(this.next_page_url).then(function () {
                    app.pageCheck();
                });
            }
        },
        prevPage: function () {
            if (this.page > 0) {
                this.page--
                this.pageCheck()
            }
        },
        getResultsPage: function (query_url) {
            this.startLoading();
            console.log(query_url)
            return fetch(query_url)
                .then(function (response) {
                    if (response.ok) {
                        return response.json();
                    }
                    if (response.status === 500) {
                        document.getElementById("loading-overlay").style.display = 'none';
                        //TODO
                    }
                    console.log(response.status, response.statusText, query_url)
                })
                .then(function (results_json) {
                    app.hitcount = results_json.count;
                    app.next_page_url = results_json.next;
                    app.prev_page_url = results_json.previous;
                    app.page = app.results.push(results_json.results) - 1;
                })
                .then(function () {
                    app.stopLoading();
                })
        },
        resetForm: function () {
            this.title = "Browse or Search"
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
            fields = [ { "label": parameter, "name": parameter, "value" : value } ]
            this.newSearch(fields, "cases")
            this.$refs.searchform.changeEndpoint("cases", fields)
        }
    },
    delimiters: ['[[', ']]'],
    template: '',

    components: {
        'search-form': {
            data: function () {
                return {
                    query: [],
                    newfield: null,
                    endpoint: 'cases',
                    fields: [{
                        name: "search",
                        label: "Full-Text Search",
                        format:"e.g. \'insurance illinois\'",
                        value: ""
                    }],
                    endpoints: endpoint_list
                }
            },
            template: '<form v-on:submit.prevent>\
                <div class="row">\
                    <template v-for="(current_fields, current_endpoint) in endpoints">\
                        <div class="col">\
                            <input type="radio" :id="current_endpoint" :value="current_endpoint" @change="changeEndpoint(endpoint)" v-model="endpoint">\
                            <label :for="current_endpoint" v-text="current_endpoint"></label>\
                        </div>\
                    </template>\
                </div>\
                <div>\
                    <div v-for="field in fields">\
                        <div class="row field_row_container">\
                            <div class="col-4 field_label_container">\
                                <label class="querylabel" :for="field[\'name\']">{{ field["label"] }}</label><br>\
                            </div>\
                            <div class="col-7 field_value_container">\
                                <template v-if="field[\'choices\']">\
                                    <select v-model=\'field["value"]\' :id=\'field["name"]\'>\
                                        <option v-for="(label, value) in choiceLoader(field[\'choices\'])" :value="value">{{ label }}</option> \
                                    </select>\
                                </template>\
                                <template v-else-if="field[\'format\']">\
                                    <input v-model=\'field["value"]\' class="queryfield" :id=\'field["name"]\' type="text" :placeholder=\'field["format"]\'>\
                                </template>\
                                <template v-else>\
                                    <input v-model=\'field["value"]\' class="queryfield" :id=\'field["name"]\' type="text">\
                                </template>\
                            </div>\
                            <div class="col-1">\
                                <button class="querybutton" v-if="fields.length > 1" @click="removeField(field[\'name\'])">&ndash;</button>\
                            </div>\
                        </div>\
                    </div>\
                    <template v-if="fields.length > 0">\
                        <div>\
                        <div class="row field_row_container">\
                            <div class="col-4 field_label_container">\
                                <select v-model="newfield" @change="fields.push(newfield)">\
                                    <option v-for="newfield in endpoints[endpoint]" v-bind:value="newfield">{{ newfield["label"] }}</option>\
                                    <option value="" disabled selected>Add a field</option>\
                                </select>\
                            </div>\
                            <div class="col-7 field_value_container">\
                                <input type="text" class="queryfield" placeholder = "add a new field" disabled>\
                            </div>\
                        </div>\
                        </div>\
                    </template>\
                </div>\
                <template v-if="fields.length > 0">\
                    <input @click="$emit(\'new-search\', fields, endpoint)" type="submit">\
                </template>\
                <template v-else>\
                    <input @click="$emit(\'new-search\', fields, endpoint)" type="submit" value="Browse All">\
                </template>\
             </form>',
            beforeMount() {
                for (endpoint in endpoint_list) {
                    for (field in endpoint_list[endpoint]){
                            if ('choices' in endpoint_list[endpoint][field]) {
                                this.choiceLoader(endpoint_list[endpoint][field].choices);
                        }
                    }
                }
            },
            methods: {
                changeEndpoint: function (new_endpoint, new_fields=[]) {
                    this.$parent.endpoint = new_endpoint // to update title
                    this.endpoint = new_endpoint;
                    this.fields = new_fields;
                    this.$emit('change-endpoint');
                    if (new_fields.length === 0 ) {
                        for (var i = this.endpoints[new_endpoint].length - 1; i >= 0; i--) {
                            if (this.endpoints[new_endpoint][i]['default']) {
                                this.fields.push(this.endpoints[new_endpoint][i]);
                            }
                        }
                    }
                },

                removeField: function (field_to_remove) {
                    for (var i = this.fields.length - 1; i >= 0; i--) {
                        if (this.fields[i]['name'] === field_to_remove) {
                            this.fields.splice(i, 1);
                        }
                    }
                },
                addField: function (field_to_add) {
                    for (var i = this.fields.length - 1; i >= 0; i--) {
                        if (this.fields[i]['name'] === field_to_add['name']) {
                            return false;
                        }
                    }
                    this.fields.push(field_to_add);
                },

                choiceLoader: function (choice) {
                    component = null;
                    if (app){
                        component = app;
                    } else if ('choices' in this.$parent) {
                        component = this.$parent;
                    }

                    if (choice in component.choices) {
                        return component.choices[choice];
                    }
                    if (choice == "whitelisted") {
                        return { "true": "Whitelisted", "false": "Not Whitelisted" }
                    }
                    component.startLoading();
                    return fetch(choice_source[choice])
                        .then(function (response) {
                            if (response.ok) {
                                return response.json();
                            }
                            if (response.status === 500) {
                                document.getElementById("loading-overlay").style.display = 'none';
                                //TODO Set up some kind of error condition
                            }
                        })
                        .then(function (results_json) {
                            component.choices[choice] = results_json;
                        })
                        .then(function () {
                            component.stopLoading();
                        })
                    }
            }
        },
        'result-list': {
            props: [
                'results',
                'endpoint',
                'hitcount',
                'page',
                'first_page',
                'last_page'
            ],
            template: '<div>\
                <div class="hitcount" v-if="hitcount">Results: {{ hitcount }}</div>\
                <button v-if="first_page !== true" @click="$emit(\'prev-page\')">&lt;&lt;Page {{ page }} </button>\
                <button v-if="last_page !== true" @click="$emit(\'next-page\')">Page {{ page + 2 }}&gt;&gt;</button>\
                <ul class="results-list">\
                    <case-result v-if=\"endpoint == \'cases\'\" v-for="result in results[page]" :result="result" :key="result.id"></case-result>\
                    <court-result v-if=\"endpoint == \'courts\'\" v-for="result in results[page]" :result="result" :key="result.id"></court-result>\
                    <jurisdiction-result v-if=\"endpoint == \'jurisdictions\'\" v-for="result in results[page]" :result="result" :key="result.id"></jurisdiction-result>\
                    <volume-result v-if=\"endpoint == \'volumes\'\" v-for="result in results[page]" :result="result" :key="result.id"></volume-result>\
                    <reporter-result v-if=\"endpoint == \'reporters\'\" v-for="result in results[page]" :result="result" :key="result.id"></reporter-result>\
                </ul>\
             </div>',
            components: {
                'case-result': {
                    props: [
                        'result'
                    ],
                    template: '\
                <li class="result">\
                  <div class="search-title">\
                    <a target="_blank" v-text="result.name_abbreviation" :href="case_browse_url(result.id)"></a>\
                  </div>\
                  <div class="search-data">\
                    <div class="result-first-row">\
                      <div class="result-first-row-left">\
                        <ul class="citation-list">\
                            <li class="citation-entry" v-for="citation in result.citations">\
                                <span class="result-citation-type">{{  citation.type  }}</span>\
                                <span class="result-citation">{{ citation.cite }} </span>\
                            </li>\
                        </ul>\
                      </div>\
                    </div>\
                    <div class="result-second-row">\
                      <div class="result-dec-date">{{ result.decision_date }}</div>\
                      <div v-if="result.court" class="result-court-name">{{ result.court.name }}</div>\
                      <div v-if="result.volume" class="result-volume-number">v. {{ result.volume.volume_number }}</div>\
                    </div>\
                  </div>\
                </li>',
                    methods: {
                        case_browse_url: function (case_id) {
                            return case_browse_url_template.replace('987654321', case_id)
                        },
                    }
                },
                'court-result': {
                    props: [
                        'result'
                    ],
                    template: '\
                    <li class="result">\
                        <div class="search-title"><a v-text="result.name" @click="$parent.$emit(\'see-cases\', \'court\', result.slug)"></a></div>\
                        <div class="search-data">\
                            <div class="result-first-row">\
                                <div class="result-first-row-left">{{ result.jurisdiction }}</div>\
                                <div class="result-first-row-left">{{ result.name_abbreviation }}</div>\
                            </div>\
                        </div>\
                    </li>',
                },
                'volume-result': {
                    props: [
                        'result'
                    ],
                    template: '\
                    <li class="result">\
                        <div class="search-title"><a :href="result.url">{{ result.reporter }} v. {{ result.volume_number }}</a></div>\
                        <div class="search-data">\
                            <div class="result-first-row">\
                                <div class="result-first-row-left">{{ result.publication_year }}</div>\
                                <div class="result-first-row-left">{{ result.jurisdiction }}</div>\
                            </div>\
                        </div>\
                    </li>'
                },
                'jurisdiction-result': {
                    props: [
                        'result'
                    ],
                    template: '\
                    <li class="result">\
                        <div class="search-title"><a v-text="" @click="$parent.$emit(\'see-cases\', \'jurisdiction\', result.slug)">{{result.name_long}} ({{ result.name }})</a></div>\
                        <div class="search-data">\
                            <div class="result-first-row">\
                                Slug: <div class="result-first-row-left">{{ result.slug }}</div>\
                                Abbr: <div class="result-first-row-left">{{ result.name_abbreviation }}</div>\
                            </div>\
                        </div>\
                    </li>'
                },
                'reporter-result': {
                    props: [
                        'result'
                    ],
                    template: '\
                    <li class="result">\
                        <div class="search-title"><a v-text="result.full_name" @click="$parent.$emit(\'see-cases\', \'reporter\', result.id)"></a></div>\
                        <div class="search-data">\
                            <div class="result-first-row">\
                                <div class="result-first-row-left"><a :href="result.url">Browse Cases</a></div>\
                                <div class="result-first-row-left">{{ result.short_name }}</div>\
                            </div>\
                        </div>\
                    </li>'
                },
            }
        }
    }
});
