import Vue from 'vue'
import Vuex from 'vuex'
import {encodeQueryData} from "../utils";
import axios from "axios";


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
    results: [],
    first_result_number: null,
    last_result_number: null,
    showLoading: false,
    previous_page: {
      'page': null,
      'url': null,
    },
    next_page: {
      'page': null,
      'url': null,
    },
    page_size: 10,
    whitelisted: importChoices.whitelisted,
    search_error: null,
    display_class: '',
    urls: importUrls,
    download_size: 10000,
    download_full_case: false,
    show_explainer: false,
    advanced_fields_shown: false,
    fields: {
      search: {
        value: null,
        label: "Full-text search",
        type: "text",
        placeholder: "Enter keyword or phrase",
        info: "Terms stemmed and combined using AND. Words in quotes searched as phrases.",
        error: null,
      },
      decision_date_min: {
        label: "Date from YYYY-MM-DD",
        placeholder: "YYYY-MM-DD",
        type: "text",
        value: null,
        error: null,
      },
      decision_date_max: {
        value: null,
        label: "Date to YYYY-MM-DD",
        placeholder: "YYYY-MM-DD",
        type: "text",
        error: null,
      },
      name_abbreviation: {
        label: "Case name abbreviation",
        value: null,
        placeholder: "Enter case name abbreviation e.g. Taylor v. Sprinkle",
        error: null,
      },
      docket_number: {
        value: null,
        label: "Docket number",
        placeholder: "e.g. Civ. No. 74-289",
        error: null,
      },
      reporter: {
        value: null,
        label: "Reporter",
        choices: importChoices.reporter,
        error: null,
      },
      jurisdiction: {
        value: null,
        label: "Jurisdiction",
        choices: importChoices.jurisdiction,
        error: null,
      },
      cite: {
        value: null,
        label: "Citation e.g. 1 Ill. 17",
        placeholder: "e.g. 1 Ill. 17",
        error: null,
      },
      court: {
        value: null,
        label: "Court",
        placeholder: "e.g. ill-app-ct",
        error: null,
      },
    },
    sort_field: {
      name: "ordering",
      value: "relevance",
      label: "Result Sorting",
      choices: [
        ["relevance", "Most Relevant First"],
        ["-decision_date", "Newest Decisions First"],
        ["decision_date", "Oldest Decisions First"]],
    },
  },
  mutations: {
    hitcount(state, value) {
      state.hitcount = value
    },
    page(state, value) {
      state.page = value
    },
    fields(state, value) {
      state.fields = value
    },
    results(state, value) {
      state.results = value
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
    page_size(state, value) {
      state.page_size = value
    },
    search_error(state, value) {
      state.search_error = value
    },
    urls(state, value) {
      state.urls = value
    },
    toggleExplainer(state) {
      state.show_explainer = !state.show_explainer;
    },
    toggleAdvanced(state) {
      state.advanced_fields_shown = !state.advanced_fields_shown;
    },
    nextPage(state, value) {
      state.next_page.url = value.url;
      state.next_page.page = value.page;
    },
    previousPage(state, value) {
      state.previous_page.url = value.url;
      state.previous_page.page = value.page;
    },
    clearAllFields(state) {
      Object.keys(state.fields).forEach(field => {
        state.fields[field].error = state.fields[field].value = null;
      });
    },
    clearField(state, field_name) {
      state.fields[field_name].value = state.fields[field_name].error = null;
    },
    clearFieldErrors(state) {
      Object.keys(state.fields).forEach(field => {
        state.fields[field]['error'] = null;
      });
    },
    setFieldValue(state, update) {
      state.fields[update.name].value = update.value;
    },
    setFieldError(state, update) {
      state.fields[update.name].value = update.error;
    }
  },
  getters: {
    hitcount: state => state.hitcount,
    page: state => state.page,
    previous_page: state => state.previous_page,
    next_page: state => state.next_page,
    fields: state => state.fields,
    results: state => state.results,
    resultsShown(state) {
        return !(!state.results)
    },
    first_result_number: state => state.first_result_number,
    last_result_number: state => state.last_result_number,
    showLoading: state => state.showLoading,
    page_size: state => state.page_size,
    choices: state => state.choices,
    search_error: state => state.search_error,
    sort_field: state => state.sort_field,
    urls: state => state.urls,
    show_explainer: state => state.show_explainer,
    advanced_fields_shown: state => state.advanced_fields_shown,
    populated_fields(state) {
      let populated = [];
      Object.keys(state.fields).forEach(key => {
        if (state.fields[key]['value']) {
          populated.push(state.fields[key])
        }
      });
      return populated
    },
    new_query_url: (state) => {
      /* assembles and returns URL */
      const params = {};

      params.page_size = state.page_size;

      // build the query parameters using the form fields
      Object.keys(state.fields).forEach(key => {
        if (state.fields[key]['value']) {
          params[key] = state.fields[key]['value'];
        }
      });

      if (state.sort_field['value']) {
        params[state.sort_field['name']] = state.sort_field['value'];
      }

      return `${state.urls.api_root}cases/?${encodeQueryData(params)}`;
    },
    download_url: (state, getters) => (download_format) => {
      return getters.new_query_url + "&format=" + download_format + (state.download_full_case ? "&full_case=true" : '');
    },
    erroredFieldList: (state) => {
      let fields_with_errors = []
      Object.keys(state.fields).forEach(key => {
        if (state.fields[key]['error']) {
          fields_with_errors.push(key);
        }
      });
      return fields_with_errors;
    },
    fieldHasError: (state) => (name) => {
      return !(!state.fields[name].error);
    },
    getField: (state) => (name) => {
      return { ...state.fields[name], ...{'name': name}};
    },
  },
  actions: {
    resetSearchResults: function ({commit}) {
      commit('hitcount', null);
      commit('page', 0);
      commit('results', []);
      commit('first_result_number', null);
      commit('last_result_number', null);
      commit('clearFieldErrors')
    },
    executeSearch: function ({commit}, url) {
      commit('showLoading', true);
      if (!url) {
        url = this.getters.new_query_url
      }
      commit('search_error', "");
      commit('clearFieldErrors', "");
      // Track current fetch operation, so we can throw away results if a fetch comes back after a new one has been
      // submitted by the user.


      axios
          .get(url)
          .then(response => {
            return response.data
          })
          .then(results_json => {
            commit('hitcount', results_json.count);

            if (results_json.next) {
              commit('nextPage', {'url': results_json.next, 'page': this.getters.page + 1})
            }
            if (results_json.previous) {
              commit('previousPage', {'url': results_json.previous, 'page': this.getters.page + 1})
            }

            commit('results', results_json.results)
          }).then(
          () => {
            commit('showLoading', false);
          }
      ).catch(error => {
        if (error.response) {
          if (error.response.status === 400) {
            // handle field errors
            Object.keys(error.response.data).forEach(field => {
              commit('setFieldError', { 'name': field, 'error': error.response.data[field]} )
            });
          } else {
            commit('search_error', "Error " + error.response.status + "- query failed: " + url);
          }
        } else if (error.request) {
          this.state.search_error = "Search error: request failed" + url + " " + error.request;
        } else {
          this.state.search_error = "Search error: " + error;
        }
        commit('showLoading', false);
        // scroll up to show error message
        alert("implement scroll to error, or different place for it");
      })

      // return fetch(this.state.new_query_url)
      //     .then((response) => {
      //       if (currentFetchID !== this.state.currentFetchID) {
      //         throw "canceled"
      //       }
      //       if (!response.ok) {
      //         throw response
      //       }
      //       return response.json();
      //     })
      //     .then((results_json) => {
      //       commit('hitcount', results_json.count);
      //
      //       // extract cursors
      //       let next_page_url = results_json.next;
      //       let prev_page_url = results_json.previous;
      //       if (this.state.page > 1 && !this.state.cursors[this.state.page - 1] && prev_page_url)
      //         this.$store.cursors[this.state.page - 1] = URL(prev_page_url).searchParams.get("cursor")
      //       if (!this.state.cursors[this.state.page + 1] && next_page_url)
      //         this.$store.cursors[this.state.page + 1] = URL(next_page_url).searchParams.get("cursor")
      //
      //       // use this.$set to set array value with reactivity -- see https://vuejs.org/v2/guide/list.html#Caveats
      //       this.$set(this.$store.results, this.$store.page, results_json.results);
      //       commit('showLoading', false);
      //     })
      //     .catch((response) => {
      //       if (response === "canceled") {
      //         return;
      //       }
      //
      //       // scroll up to show error message
      //       commit('showLoading', false);
      //       alert("implement scroll to error, or different place for it");
      //
      //       if (response.status === 400 && this.state.field_errors) {
      //         // handle field errors
      //         return response.json().then((object) => {
      //           this.state.field_errors = object;
      //           throw response;
      //         });
      //       }
      //
      //       if (response.status) {
      //         // handle non-field API errors
      //         this.state.search_error = "Search error: API returned " +
      //             response.status + " for the query " + this.state.new_query_url;
      //       } else {
      //         // handle connection errors
      //         this.state.search_error = "Search error: failed to load results from " + this.state.new_query_url;
      //       }
      //
      //       console.log("Search error:", response);  // eslint-disable-line
      //       throw response;  // in case callers want to do further error handling
      //     }).catch(() => {
      //     });


    },
    pageForward: function (commit) {
      if (this.getters.next_page.url) {
        commit('page', this.getters.page - 1);
        commit('execute_query', this.getters.next_page.url);
      }
    },
    pageBackward: function (commit) {
      if (this.getters.previous_page.url) {
        commit('page', this.getters.page + 1);
        commit('execute_query', this.getters.previous_page.url);
      }
    },
  }
});


export default store;