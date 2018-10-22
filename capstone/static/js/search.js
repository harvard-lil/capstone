const jurisdiction_list = {
    "ala": "Alabama",
    "alaska": "Alaska",
    "am-samoa": "American Samoa",
    "ariz": "Arizona",
    "ark": "Arkansas",
    "cal": "California",
    "colo": "Colorado",
    "conn": "Connecticut",
    "dakota-territory": "Dakota Territory",
    "dc": "District of Columbia",
    "del": "Delaware",
    "fla": "Florida",
    "ga": "Georgia",
    "guam": "Guam",
    "haw": "Hawaii",
    "idaho": "Idaho",
    "ill": "Illinois",
    "ind": "Indiana",
    "iowa": "Iowa",
    "kan": "Kansas",
    "ky": "Kentucky",
    "la": "Louisiana",
    "mass": "Massachusetts",
    "md": "Maryland",
    "me": "Maine",
    "mich": "Michigan",
    "minn": "Minnesota",
    "miss": "Mississippi",
    "mo": "Missouri",
    "mont": "Montana",
    "native-american": "Native American",
    "navajo-nation": "Navajo Nation",
    "nc": "North Carolina",
    "nd": "North Dakota",
    "neb": "Nebraska",
    "nev": "Nevada",
    "nh": "New Hampshire",
    "nj": "New Jersey",
    "nm": "New Mexico",
    "n-mar-i": "Northern Mariana Islands",
    "ny": "New York",
    "ohio": "Ohio",
    "okla": "Oklahoma",
    "or": "Oregon",
    "pa": "Pennsylvania",
    "pr": "Puerto Rico",
    "regional": "Regional",
    "ri": "Rhode Island",
    "sc": "South Carolina",
    "sd": "South Dakota",
    "tenn": "Tennessee",
    "tex": "Texas",
    "us": "United States",
    "utah": "Utah",
    "va": "Virginia",
    "vi": "Virgin Islands",
    "vt": "Vermont",
    "wash": "Washington",
    "wis": "Wisconsin",
    "w-va": "West Virginia",
    "wyo": "Wyoming"
};

const endpoint_list = {
    "cases": [
        {
            name: "name_abbreviation",
            label: "Case Name Abbreviation",
            value: ""
        },
        {
            name: "decision_date_min",
            label: "Decision Date Earliest",
            format: "YYYY-MM-DD"
        },
        {
            name: "decision_date_max",
            value: "",
            label: "Decision Date Latest",
            format: "YYYY-MM-DD"
        },
        {
            name: "docket_number",
            value: "",
            label: "Docket Number"
        },
        {
            name: "citation",
            value: "",
            label: "Citation"
        },
        {
            name: "reporter",
            value: "",
            label: "Reporter"
        },
        {
            name: "court",
            value: "",
            label: "Court"
        },
        {
            name: "jurisdiction",
            value: "",
            label: "Jurisdiction",
            choices: jurisdiction_list
        },
        {
            name: "search",
            value: "",
            label: "Name Abbreviation",
            default: true
        }
    ],
    "courts": [
        {
            name: "name",
            value: "",
            label: "Name"
        },
        {
            name: "name_abbreviation",
            value: "",
            label: "Name Abbreviation"
        },
        {
            name: "jurisdiction",
            value: "",
            label: "Jurisdiction",
            choices: jurisdiction_list,
            default: true
        }
    ]
};


var app = new Vue({
    el: '#app',
    data: {
        title: "Browse or Search",
        result_list: [],
        hitcount: null,
        next_100_url: '',
        current_subset: 0,
        current_page: 0,
        all_results: [],
        results: [''],
        api_url: search_url,
        endpoint: '',
        subset_size: 10,
        last_subset: true,
        first_subset: true,
    },
    methods: {
        newSearch: function (fields, endpoint) {
            // use all the fields and endpoint to build the query url
            this.endpoint = endpoint;
            this.all_results = [];
            this.hitcount = null;
            this.current_subset = 0;
            this.current_page = 0;
            //this.prev_100_url = null;
            var query_url = this.api_url + endpoint + "/";
            if (fields.length > 0) {
                query_url += "?";
                for (var i = fields.length - 1; i >= 0; i--) {
                    if (i !== fields.length - 1) {
                        query_url += "&";
                    }
                    if (fields[i]['value']) {
                        query_url += (fields[i]['name'] + "=" + fields[i]['value']);
                    }
                }
            }
            this.next_100_url = query_url;
            this.getNextSubset();
        },
        getResultsPage: function (query_url) {
            document.getElementById("loading-overlay").style.display = 'block';
            self = this;
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
                    self.hitcount = results_json.count;
                    self.next_100_url = results_json.next;
                    //this.prev_url= results_json.previous;
                    subset_index = 0;
                    subsets = [];
                    subsets[subset_index] = [];

                    // split the results up into subsets for easier display
                    for (result in results_json.results) {

                        if (subsets[subset_index].length > 0 && subsets[subset_index].length === self.subset_size) {
                            subset_index++;
                            subsets[subset_index] = [];
                        }
                        subsets[subset_index].push(results_json.results[result]);
                    }
                    self.current_subset = 0;
                    // js push returns the number of elements in the array
                    self.current_page = self.all_results.push(subsets) - 1;
                })
                .then(function () {
                    document.getElementById("loading-overlay").style.display = 'none';
                })
        },
        getNextSubset: function () {
            self = this
            // this is stupid but labelling these long variables makes it more readable
            subset_count_this_page = null;
            current_subset_count_number = null;
            if (this.all_results !== undefined && this.all_results.length !== 0) {
                subset_count_this_page = this.all_results[this.current_page].length ? this.all_results[this.current_page] : null;
                current_subset_count_number = this.current_subset + 1 ? this.all_results[this.current_page] : null;
            }

            // check to see if it's a new search, or we're at the end of our subset and there's another page we can grab
            if (this.all_results === [] || (subset_count_this_page === current_subset_count_number && this.next_100_url)) {
                this.getResultsPage(this.next_100_url).then(function () {
                    subset_count_this_page = self.all_results[self.current_page].length;
                    current_subset_count_number = self.current_subset + 1; //as opposed to the array index number

                    if (self.next_100_url || subset_count_this_page > current_subset_count_number) {
                        self.last_subset = false;
                    } else {
                        self.last_subset = true;
                    }
                    self.results = self.all_results[self.current_page][self.current_subset]
                });
                return
            } else if (subset_count_this_page === current_subset_count_number && this.all_results[this.current_page + 1]) {
                this.current_subset = 0;
                this.current_page++;
            } else {
                this.current_subset++
            }

            // refresh these
            subset_count_this_page = this.all_results[this.current_page].length;
            current_subset_count_number = this.current_subset + 1; //as opposed to the array index number

            if (this.next_100_url || subset_count_this_page > current_subset_count_number) {
                this.last_subset = false;
            } else {
                this.last_subset = true;
            }
            this.results = this.all_results[this.current_page][this.current_subset]
        },
        getPrevSubset: function () {
            if (this.current_subset > 0) {
                this.current_subset--;
            } else if (this.current_subset === 0 && this.current_page > 0) {
                this.current_subset--;
                this.current_page--;
            }

            if (this.current_page > 0 || this.current_subset > 0) {
                this.first_subset = false;
            } else {
                this.first_subset = true;
            }
            this.results = this.all_results[this.current_page][this.current_subset]
        },
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
                        label: "Full Text Search",
                        value: ""
                    }],
                    endpoints: endpoint_list
                }
            },
            template: '<form v-on:submit.prevent>\
                <div>\
                    Currently Searching: <select v-model="endpoint" @change="changeEndpoint(endpoint)">\
                        <option v-for="(current_fields, current_endpoint) in endpoints">{{ current_endpoint }}</option>\
                    </select>\
                </div>\
                <ul>\
                    <li v-for="field in fields">\
                        <label class="querylabel" :for="field[\'name\']">{{ field["label"] }}</label><br>\
                        <template v-if="field[\'choices\']">\
                            <select v-model=\'field["value"]\' :id=\'field["name"]\'>\
                                <option v-for="(label, value) in field[\'choices\']" :value="value">{{ label }}</option> \
                            </select>\
                        </template>\
                        <template v-else-if="field[\'format\']">\
                            <input v-model=\'field["value"]\' class="queryfield" :id=\'field["name"]\' type="text" :placeholder=\'field["format"]\'>\
                        </template>\
                        <template v-else>\
                            <input v-model=\'field["value"]\' class="queryfield" :id=\'field["name"]\' type="text">\
                        </template>\
                        <button class="querybutton" v-if="fields.length > 1" @click="removeField(field[\'name\'])">&ndash;</button>\
                        <br>\
                    </li>\
                    <li>\
                    Add a field:\
                        <select v-model="newfield" @change="fields.push(newfield)">\
                            <option v-for="newfield in endpoints[endpoint]" v-bind:value="newfield">{{ newfield["label"] }}</option>\
                        </select>\
                    </li>\
                </ul>\
                <input @click="getSearch()" type="submit">\
             </form>',
            methods: {
                changeEndpoint: function (new_endpoint) {
                    this.endpoint = new_endpoint;
                    this.fields = [];

                    for (var i = this.endpoints[new_endpoint].length - 1; i >= 0; i--) {
                        if (this.endpoints[new_endpoint][i]['default']) {
                            this.fields.push(this.endpoints[new_endpoint][i]);
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
                getSearch: function () {
                    this.$emit('new-search', this.fields, this.endpoint);
                }
            }
        },
        'result-list': {
            props: [
                'results',
                'endpoint',
                'hitcount'
            ],
            template: '<div>\
                <span class="hitcount" v-if="hitcount">Results: {{ hitcount }}</span>\
                <ul class="results-list">\
                    <case-result v-if=\"endpoint == \'cases\'\" v-for="result in results" :result="result" :key="result.id"></case-result>\
                    <court-result v-if=\"endpoint == \'courts\'\" v-for="result in results" :result="result" :key="result.id"></court-result>\
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
                    <a v-text="result.name_abbreviation" :href="case_browse_url(result.id)"></a>\
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
                    case_browse_url: function(case_id) {
                            return case_browse_url_template.replace('987654321', case_id)
                        }
                    }
                },
                'court-result': {
                    props: [
                        'result'
                    ],
                    template: '\
                    <li class="result">\
                        <div class="search-title"><a v-text="result.name" :href="result.url"></a></div>\
                        <div class="search-data">\
                            <div class="result-first-row">\
                                <div class="result-first-row-left">{{ result.id }}</div>\
                                <div class="result-first-row-left">{{ result.name_abbreviation }}</div>\
                            </div>\
                            <div class="result-second-row">\
                                <div class="result-dec-date"></div>\
                                <div class="result-court-name">{{ result.jurisdiction }}</div>\
                                <div class="result-volume-number"></div>\
                            </div>\
                        </div>\
                    </li>'
                },
            }
        }
    }
});