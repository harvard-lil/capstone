// This is essentially each endpoint with its API interface
const endpoint_list = {
    cases: [
        {
            name: "search",
            value: "",
            label: "Full-Text Search",
            default: true,
            format: "e.g. \'insurance\' illinois",
            info: ""
        },
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
            format: "e.g. Civ. No. 74-289",
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
        }
    ],
    courts: [
        {
            name: "slug",
            value: "",
            label: "Slug",
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
        title: "Search",
        hitcount: null,
        next_page_url: null,
        prev_page_url: null,
        page: 0,
        results: [],
        api_url: search_url,
        endpoint: 'cases', // only used in the title in search.html. The working endpoint is in the searchform component
        page_size: 10,
        last_page: true,
        first_page: true,
        choices: {}
    },
    methods: {
        // Each time a new search is queued up
        newSearch: function (fields, endpoint) {
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
                    fields: [endpoint_list['cases'][0]],
                    endpoints: endpoint_list
                }
            },
            template: '<form v-on:submit.prevent>\
                    <div class="row">\
                        <div class="col-12">\
                            <ul class="nav nav-tabs">\
                                <li class="search-tab" v-for="(current_fields, current_endpoint) in endpoints">\
                                    <a v-if="current_endpoint == endpoint" @click="changeEndpoint(current_endpoint)" class="nav-link active">{{ current_endpoint }}</a>\
                                    <a v-else="current_endpoint == endpoint" @click="changeEndpoint(current_endpoint)" class="nav-link">{{ current_endpoint }}</a>\
                                </li>\
                            </ul>\
                        </div>\
                    </div> \
                    <div id="searchform">\
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
                                    <div class="remfield">\
                                        <button v-if="fields.length > 1" class="field-button" @click="removeField(field[\'name\'])">&ndash;</button>\
                                        <button v-if="fields.length <= 1" class="field-button disabled">&ndash;</button>\
                                    </div>\
                                </div>\
                            </div>\
                        </div>\
                    </div>\
                        <div class="row field_row_container">\
                            <div class="col-4 field_label_container">\
                            </div>\
                                <div class="col-7 field_value_container">\
                                    <template v-if="fields.length > 0">\
                                        <div class="dropdown addfield">\
                                            <button class="dropdown-toggle add-field-button btn-block" type="button" id="dropdownMenuButton" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false">Add Field</button>\
                                            <div class="dropdown-menu" aria-labelledby="dropdownMenuButton">\
                                                <a class="dropdown-item" v-for="newfield in currentFields(endpoint)" @click="addField(newfield)" href="#">{{ newfield["label"] }}</a>\
                                            </div>\
                                        </div>\
                                    </template>\
                                </div>\
                            <div class="col-1">\
                                <div class="remfield">\
                                </div>\
                            </div>\
                        </div>\
                        <div class="search-button-row row">\
                            <div class="col-11 text-right">\
                                <input @click="$emit(\'new-search\', fields, endpoint)" type="submit" value="Search">\
                            </div>\
                        </div>\
                    </form>\
                ',
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
                    },
                currentFields: function (endpoint) {
                    return_list = []
                    for (field in endpoint_list[endpoint]) {
                        if (!this.fields.includes(endpoint_list[endpoint][field])) {
                            return_list.push(endpoint_list[endpoint][field])
                        }
                    }
                    return return_list
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
                <ul class="results-list">\
                    <case-result v-if=\"endpoint == \'cases\'\" v-for="result in results[page]" :result="result" :key="result.id"></case-result>\
                    <court-result v-if=\"endpoint == \'courts\'\" v-for="result in results[page]" :result="result" :key="result.id"></court-result>\
                    <jurisdiction-result v-if=\"endpoint == \'jurisdictions\'\" v-for="result in results[page]" :result="result" :key="result.id"></jurisdiction-result>\
                    <reporter-result v-if=\"endpoint == \'reporters\'\" v-for="result in results[page]" :result="result" :key="result.id"></reporter-result>\
                </ul>\
                <div v-if="this.$parent.results.length != 0" class="row">\
                    <div class="col-6">\
                        <button class="btn btn-sm" v-if="first_page !== true" @click="$emit(\'prev-page\')">&lt;&lt; Prev Page {{ page }} </button>\
                        <button class="btn btn-sm disabled" v-else disabled>&lt;&lt; Prev Page</button>\
                    </div>\
                    <div class="col-6 text-right">\
                        <button class="btn btn-sm" v-if="last_page !== true" @click="$emit(\'next-page\')">Next Page {{ page + 2 }}&gt;&gt;</button>\
                        <button class="btn btn-sm disabled" v-else disabled>Next Page &gt;&gt;</button>\
                    </div>\
                </div>\
            </div>',
            methods: {
                case_view_url: function (case_id) {
                    return case_view_url_template.replace('987654321', case_id)
                },
                metadata_view_url: function (endpoint, id) {
                    return case_view_url_template.replace('987654321', id).replace('/case/', "/" + endpoint + "/")
                },
            },
            components: {
                'case-result': {
                    props: [
                        'result'
                    ],
                    template: '\
                <li class="result">\
                    <div class="result-title row">\
                        <div class="row">\
                            <a target="_blank" v-text="result.name_abbreviation" :href="$parent.case_view_url(result.id)"></a>\
                        </div>\
                    </div>\
                    <div class="result-data">\
                        <div class="row">\
                            <div class = "col-12">\
                                <ul class="citation-list">\
                                    <li class="citation-entry" v-for="citation in result.citations">\
                                        <span class="result-citation-type">{{  citation.type  }}</span>\
                                        <span class="result-citation">{{ citation.cite }} </span>\
                                    </li>\
                                </ul>\
                            </div>\
                        </div>\
                        <div class="row">\
                            <div class="col-3">{{ result.decision_date }}</div>\
                            <div class="col-4" v-if="result.court" >{{ result.court.name }}, volume {{ result.jurisdiction.volume_number }}</div>\
                        </div>\
                        <div class="row">\
                            <div v-text="result.name" class="full-name col-12">\</div>\
                        </div>\
                    </div>\
                </li>'
                },
                'court-result': {
                    props: [
                        'result'
                    ],
                    template: '\
                        <li class="result">\
                            <div class="result-title row">\
                                <div class="row">\
                                    <div class="result-title col-12">\
                                        <a target="_blank" v-text="result.name_abbreviation" :href="$parent.metadata_view_url(\'court\', result.id)"></a>\
                                    </div>\
                                </div>\
                            </div>\
                            <div class="result-data">\
                                <div class="row">\
                                    <div class="col-6">\
                                        <span class="result-data-label">Abbreviation:</span> {{ result.name_abbreviation }}\
                                    </div>\
                                    <div class = "col-3">\
                                        <span class="result-data-label">Jurisdiction:</span> {{ result.jurisdiction }}\
                                    </div>\
                                    <div class="col-3 text-right"> \
                                        <button @click="$parent.$emit(\'see-cases\', \'court\', result.slug)">Cases</button>\ \
                                    </div>\
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
                            <div class="result-title row">\
                                <div class="row">\
                                    <div class="result-title col-12">\
                                        <a target="_blank" v-text="result.name_long" :href="$parent.metadata_view_url(\'jurisdiction\', result.id)"></a>\
                                    </div>\
                                </div>\
                            </div>\
                            <div class="result-data">\
                                <div class="row">\
                                    <div class="col-6">\
                                        <span class="result-data-label">Abbreviation:</span> {{ result.name }}\
                                    </div>\
                                    <div class = "col-4">\
                                        <span class="result-data-label">Slug:</span> {{ result.slug }}\
                                    </div>\
                                    <div class="col-2 text-right"> \
                                        <button @click="$parent.$emit(\'see-cases\', \'jurisdiction\', result.slug)">Cases</button>\ \
                                    </div>\
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
                            <div class="result-title row">\
                                <div class="row">\
                                    <div class="result-title col-12">\
                                        <a target="_blank" v-text="result.full_name" :href="$parent.metadata_view_url(\'reporter\', result.id)"></a>\
                                    </div>\
                                </div>\
                            </div>\
                            <div class="result-data">\
                                <div class="row">\
                                    <div class="col-9">\
                                        <span class="result-data-label">Abbreviation:</span> {{ result.short_name }}\
                                    </div>\
                                    <div class="col-3 text-right"> \
                                        <button @click="$parent.$emit(\'see-cases\', \'reporter\', result.id)">Cases</button>\ \
                                    </div>\
                                </div>\
                            </div>\
                        </li>'
                },
            }
        }
    }
});
