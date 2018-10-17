const jurisdictions = {
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
}


var results = Vue.component('result-list', {
    data: function () {
        return {
            case_results: [],
            court_results: [],
            volume_results: [],
            reporter_results: [],
            jurisdiction_results: [],
        }
    },
    template: '<ul class="results-list">\
                <case-result v-for="result in case_results" :key="result.id"></case-result>\
                <court-result v-for="result in court_results" :key="result.id"></court-result>\
                <jurisdiction-result v-for="result in jurisdiction_results" :key="result.id"></jurisdiction-result>\
                <volume-result v-for="result in volume_results" :key="result.id"></volume-result>\
                <reporter-result v-for="result in reporter_results" :key="result.id"></reporter-result>\
             </ul>',
    methods: {
        recieveResults: function (items, endpoint) {
            if (endpoint == "cases") {
                this.case_results = items
            }

        }
    }
});

Vue.component('search', {
    data: function () {
        return {
            query: [],
            newfield: null,
            endpoint: 'cases',
            url: search_url,
            fields: [{
                name: "search",
                label: "Full Text Search",
                value: "",
            }],
            endpoints: {
                "cases": [
                    {
                        name: "name_abbreviation",
                        label: "Case Name Abbreviation",
                        value: "",
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
                        label: "Docket Number",
                    },
                    {
                        name: "citation",
                        value: "",
                        label: "Citation",
                    },
                    {
                        name: "reporter",
                        value: "",
                        label: "Reporter",
                    },
                    {
                        name: "court",
                        value: "",
                        label: "Court",
                    },
                    {
                        name: "jurisdiction",
                        value: "",
                        label: "Jurisdiction",
                        choices: jurisdictions
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
                        label: "Name",
                    },
                    {
                        name: "name_abbreviation",
                        value: "",
                        label: "Name Abbreviation",
                    },
                    {
                        name: "jurisdiction",
                        value: "",
                        label: "Jurisdiction",
                        choices: jurisdictions,
                        default: true
                    }
                ]
            },
        }
    },
    template: '<form v-on:submit.prevent>\
                <div  v-for="field in fields">\
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
                </div>\
                <input @click="getSearch(\'asda\')" type="submit">\
                <select v-model="endpoint" @change="changeEndpoint(endpoint)">\
                    <option v-for="(current_fields, current_endpoint) in endpoints">{{ current_endpoint }}</option>\
                </select>\
                <select v-model="newfield" @change="fields.push(newfield)">\
                    <option v-for="newfield in endpoints[endpoint]" v-bind:value="newfield" @>{{ newfield["label"] }}</option>\
                </select>\
             </form>',
    methods: {
        changeEndpoint: function (new_endpoint) {
            this.endpoint = new_endpoint
            this.fields = []

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
            document.getElementById("loading-overlay").style.display = 'block';

            // use all the props to build the query url
            query_url = this.url + this.endpoint + "/"
            if (this.fields.length > 0) {
                query_url += "?";
                for (var i = this.fields.length - 1; i >= 0; i--) {
                    if (i !== this.fields.length - 1) {
                        query_url += "&";
                    }
                    if (this.fields[i]['value']) {
                        query_url += (this.fields[i]['name'] + "=" + this.fields[i]['value']);
                    }
                }
            }

            //
            fetch(query_url)
                .then(function (response) {
                    if (response.ok) {

                        return response.json();
                    }
                    if (response.status == 500) {
                        document.getElementById("loading-overlay").style.display = 'none';
                        //TODO
                    }
                    console.log(response.status, response.statusText)
                })
                .then(function (results_json) {
                    console.log(results.case_results)
                    result = {
                        name_abbreviation: "dsadsa",
                        citations: [],
                        decision_date: "asdsa",
                        volume: "asdasdsa",
                        reporter: "dsadas",
                        court: "dsadsa",
                        jurisdiction: "asdasdsa",
                        url: "adsads",
                        first_page: "asdsadsa",
                        last_page: "dsadsadsa"
                    }
                    //
                    // TODO— this nneeds to be passed through some sort of parental bus via 'app'
                    results.recieveResults([result, result, result, result]);
                    console.log(results.case_results)
                    console.log(results_json);
                })
                .then(function () {
                    document.getElementById("loading-overlay").style.display = 'none';
                });
        }
    }
});

Vue.component('case-result', {
    data: function () {
        return {
            name_abbreviation: "",
            citations: [],
            decision_date: "",
            volume: "",
            reporter: "",
            court: "",
            jurisdiction: "",
            url: "",
            first_page: "",
            last_page: "",
        }
    },
    template: '<li>\
                  <div class="search-title"><a v-text="name_abbreviation" :href="url"></a></div>\
                  <div class="search-data">\
                    <div class="result-first-row">\
                      <div class="result-first-row-left">\
                        <ul class="citation-list">\
                        <li class="citation-entry" v-for="citation in citations">\
                          <span class="result-citation-type">[[ citation.type ]]</span>\
                          <span class="result-citation">[[ citation.cite ]]</span>\
                        </li>\
                      </ul>\
                      </div>\
                    </div>\
                    <div class="result-second-row">\
                      <div class="result-dec-date">1819-12</div>\
                      <div class="result-court-name">Illinois Appellate Court Reports</div>\
                      <div class="result-volume-number">v. 23</div>\
                    </div>\
                  </div>\
                </li>'
});

var app = new Vue({
    el: '#app',
    data: {
        title: "Browse or Search",
        result_list: []
    },
    methods: {
        handleSearch: function () {
            console.log("wow")
        }
    },
    delimiters: ['[[', ']]'],
    template: '',
});