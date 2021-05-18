import Vue from 'vue'
import Vuex from 'vuex'

Vue.use(Vuex);
const store = new Vuex.Store({
    state: {
        test: 'test',
        hitcount: null,
      page: 0,
      fields: [],
      chosen_fields: [], // deep copy of fields to show in results
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
      display_class: '',
      endpoints: {
        cases: [
          {
            name: "search",
            value: "",
            label: "Full-text search",
            type: "text",
            placeholder: "Enter keyword or phrase",
            info: "Terms stemmed and combined using AND. Words in quotes searched as phrases.",
            default: true,
          },
          {
            name: "decision_date_min",
            label: "Date from YYYY-MM-DD",
            placeholder: "YYYY-MM-DD",
            type: "text",
            value: "",
          },
          {
            name: "decision_date_max",
            value: "",
            label: "Date to YYYY-MM-DD",
            placeholder: "YYYY-MM-DD",
            type: "text",
          },
          {
            name: "name_abbreviation",
            label: "Case name abbreviation",
            value: "",
            placeholder: "Enter case name abbreviation e.g. Taylor v. Sprinkle",
          },
          {
            name: "docket_number",
            value: "",
            label: "Docket number",
            placeholder: "e.g. Civ. No. 74-289",
          },
          {
            name: "reporter",
            value: "",
            label: "Reporter",
            choices: 'reporter',
          },
          {
            name: "jurisdiction",
            value: "",
            label: "Jurisdiction",
            choices: 'jurisdiction',
          },
          {
            name: "cite",
            value: "",
            label: "Citation e.g. 1 Ill. 17",
            placeholder: "e.g. 1 Ill. 17",
          },
          {
            name: "court",
            value: "",
            label: "Court",
            placeholder: "e.g. ill-app-ct",
            hidden: true,
          },
        ],
        courts: [
          {
            name: "name",
            value: "",
            label: "Name e.g. 'Illinois Supreme Court'",
            placeholder: "e.g. 'Illinois Supreme Court'",
            default: true,
          },
          {
            name: "jurisdiction",
            value: "",
            label: "Jurisdiction",
            choices: 'jurisdiction',
          },
          {
            name: "name_abbreviation",
            value: "",
            placeholder: "e.g. 'Ill.'",
            label: "Name abbreviation e.g. 'Ill.'",
          },
          {
            name: "slug",
            value: "",
            label: "Slug e.g. ill-app-ct",
            placeholder: "e.g. ill-app-ct",
          },
        ],
        jurisdictions: [
          {
            name: "name_long",
            value: "",
            label: "Long Name e.g. 'Illinois'",
            default: true,
          },
          {
            name: "name",
            value: "",
            label: "Name e.g. 'Ill.'",
          },
          {
            name: "whitelisted",
            value: "",
            label: "Whitelisted Jurisdiction",
            choices: 'whitelisted',
            info: "Whitelisted jurisdictions are not subject to the 500 case per day access limitation."
          }
        ],
        reporters: [
          {
            name: "full_name",
            value: "",
            label: "Full Name",
            default: true,
          },
          {
            name: "jurisdiction",
            value: "",
            label: "Jurisdiction",
            choices: 'jurisdiction',

          },
          {
            name: "short_name",
            value: "",
            label: "Short Name",
            placeholder: "e.g. 'Ill. App.'",
          },

          {
            name: "start_year",
            value: "",
            type: "number",
            min: "1640",
            max: "2018",
            label: "Start Year",
            placeholder: "e.g. '1893'",
            info: "Year in which the reporter began publishing."
          },
          {
            name: "end_year",
            value: "",
            type: "number",
            min: "1640",
            max: "2018",
            label: "End Year",
            placeholder: "e.g. '1894'",
            info: "Year in which the reporter stopped publishing."
          },

        ]
      },
      sort_field: {
        name: "ordering",
        value: "relevance",
        label: "Result Sorting",
        choices: 'sort',
      },
      query_url: '',
    },
    mutations: {
        updateTest(state, value) {
            state.text = value
        },
    },
    getters: {
        test: (state) => {
            return state.test
        },
        mobiletest: state => state.test,
    },
    actions: {
        requestUpdateAdmin: function ({commit}) {
            console.log(commit)
        },
    }
});


export default store;