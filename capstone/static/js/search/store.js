import Vue from 'vue'
import Vuex from 'vuex'


// defined in template
// eslint-disable-next-line
const importUrls = urls;
// eslint-disable-next-line
const importChoices = choices;

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
      choices: importChoices,
      cursor: null,
      last_page: true,
      first_page: true,
      field_errors: {},
      search_error: null,
      display_class: '',
      currentFetchID: null,
      urls: importUrls,
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
          state.updateTest = value
      },
      hitcount(state, value) {
            state.hitcount = value
      },
      page(state, value) {
            state.page = value
      },
      fields(state, value) {
            state.fields = value
      },
      chosen_fields(state, value) {
            state.chosen_fields = value
      },
      results(state, value) {
            state.results = value
      },
      resultsType(state, value) {
            state.resultsType = value
      },
      resultsShown(state, value) {
            state.resultsShown = value
      },
      first_result_number(state, value) {
            state.first_result_number = value
      },
      last_result_number(state, value) {
            state.last_result_number = value
      },
      showLoading(state, value) {
            state.showLoading = value
      },
      cursors(state, value) {
            state.cursors = value
      },
      endpoint(state, value) {
            state.endpoint = value
      },
      page_size(state, value) {
            state.page_size = value
      },
      choices(state, value) {
            state.choices = value
      },
      cursor(state, value) {
            state.cursor = value
      },
      last_page(state, value) {
            state.last_page = value
      },
      first_page(state, value) {
            state.first_page = value
      },
      field_errors(state, value) {
            state.field_errors = value
      },
      search_error(state, value) {
            state.search_error = value
      },
      endpoints(state, value) {
            state.endpoints = value
      },
      sort_field(state, value) {
            state.sort_field = value
      },
      query_url(state, value) {
            state.query_url = value
      },
      currentFetchID(state, value) {
        state.currentFetchID = value
      },
      urls(state, value) {
        state.urls = value
      },
    },
    getters: {
      hitcount:  state => state.hitcount,
      page:  state => state.page,
      fields:  state => state.fields,
      chosen_fields:  state => state.chosen_fields, // deep copy of fields to show in results
      results:  state => state.results,
      resultsType:  state => state.resultsType,
      resultsShown:  state => state.resultsShown,
      first_result_number: state => state.first_result_number,
      last_result_number:  state => state.last_result_number,
      showLoading:  state => state.showLoading,
      cursors:  state => state.cursors,
      endpoint:  state => state.endpoint,
      page_size:  state => state.page_size,
      choices:  state => state.choices,
      cursor:  state => state.cursor,
      last_page:  state => state.last_page,
      first_page:  state => state.first_page,
      field_errors:  state => state.field_errors,
      search_error:  state => state.search_error,
      endpoints:  state => state.endpoints,
      sort_field:  state => state.sort_field,
      query_url:  state => state.query_url,
      currentFetchID:  state => state.currentFetchID,
      urls:  state => state.urls,
    },
    actions: {
        getCursorFromUrl: function ({commit}) {
            console.log(commit)
        },
        resetSearchResults: function ({commit}) {
            console.log(commit)
        },
        assembleUrl: function ({commit}) {
          console.log(commit)
        },
        updateQueryUrl: function ({commit}) {
          console.log(commit)
        },
    }
});


export default store;