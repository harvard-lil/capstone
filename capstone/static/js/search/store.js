import Vue from 'vue'
import Vuex from 'vuex'
import {encodeQueryData} from "../utils";
import axios from "axios";
import router from './router'

// defined in template
const importUrls = urls; // eslint-disable-line
const importChoices = choices; // eslint-disable-line


Vue.use(Vuex);
const store = new Vuex.Store({
  state: {
    test: 'test',
    hitcount: null,
    page: 1,
    cursor: null,
    results: [],
    resultsShown: false,
    first_result_number: null,
    last_result_number: null,
    showLoading: false,
    previous_page_url: null,
    next_page_url: null, 
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
        placeholder: "Enter keyword or phrase",
        info: "Terms stemmed and combined using AND. Words in quotes searched as phrases.",
        highlight_field: false,
        highlight_explainer: false,
        error: null,
      },
      decision_date_min: {
        label: "Date from YYYY-MM-DD",
        placeholder: "YYYY-MM-DD",
        value: null,
        highlight_field: false,
        highlight_explainer: false,
        error: null,
      },
      decision_date_max: {
        value: null,
        label: "Date to YYYY-MM-DD",
        placeholder: "YYYY-MM-DD",
        highlight_field: false,
        highlight_explainer: false,
        error: null,
      },
      name_abbreviation: {
        label: "Case name abbreviation",
        value: null,
        placeholder: "Enter case name abbreviation e.g. Taylor v. Sprinkle",
        highlight_field: false,
        highlight_explainer: false,
        error: null,
      },
      docket_number: {
        value: null,
        label: "Docket number",
        placeholder: "e.g. Civ. No. 74-289",
        highlight_field: false,
        highlight_explainer: false,
        error: null,
      },
      reporter: {
        value: null,
        label: "Reporter",
        choices: importChoices.reporter,
        highlight_field: false,
        highlight_explainer: false,
        error: null,
      },
      jurisdiction: {
        value: null,
        label: "Jurisdiction",
        choices: importChoices.jurisdiction,
        highlight_field: false,
        highlight_explainer: false,
        error: null,
      },
      cite: {
        value: null,
        label: "Citation e.g. 1 Ill. 17",
        placeholder: "e.g. 1 Ill. 17",
        highlight_field: false,
        highlight_explainer: false,
        error: null,
      },
      court: {
        value: null,
        label: "Court",
        placeholder: "e.g. ill-app-ct",
        highlight_field: false,
        highlight_explainer: false,
        error: null,
      },
    },
    ordering: {
      value: "relevance",
      label: "Result Sorting",
      choices: [
        ["relevance", "Most Relevant First"],
        ["-decision_date", "Newest Decisions First"],
        ["decision_date", "Oldest Decisions First"]],
      error: null,
      highlight_field: false,
      highlight_explainer: false,
    },
  },
  mutations: {
    hitcount(state, value) {
      state.hitcount= value;
    },
    page(state, value) {
      state.page= value;
    },
    cursor(state, value) {
      state.cursor= value;
    },
    results(state, value) {
      state.results= value;
    },
    resultsShown(state, value) {
      state.results= value;
    },
    first_result_number(state, value) {
      state.first_result_number= value;
    },
    last_result_number(state, value) {
      state.last_result_number= value;
    },
    showLoading(state, value) {
      state.resultsShown = true; // we really only want to have this not set when the page first loads w/no params
      state.showLoading= value;
    },
    page_size(state, value) {
      state.page_size= value;
    },
    search_error(state, value) {
      state.search_error= value;
    },
    toggleExplainer(state) {
      state.show_explainer = !state.show_explainer;
    },
    toggleAdvanced(state) {
      state.advanced_fields_shown = !state.advanced_fields_shown;
    },
    showAdvanced(state) {
      state.advanced_fields_shown = true;
    },
    next_page_url(state, value) {
      state.next_page_url = value;
    },
    previous_page_url(state, value) {
      state.previous_page_url = value;
    },
    clearAllFields(state, dispatch) {
      state.ordering.value = 'relevance';
      state.ordering.error = null;
      Object.keys(state.fields).forEach(field => {
        state.fields[field].error = state.fields[field].value = null;
      });
      dispatch('updateQueryParameters', {})
    },
    clearField(state, field_name) {
      if (name === 'ordering') {
        state.ordering.error = null;
        state.ordering.value = 'relevance';
      }
      state.fields[field_name].value = state.fields[field_name].error = null;
    },
    clearFieldErrors(state) {
      state.ordering.error = null;
      Object.keys(state.fields).forEach(field => {
        state.fields[field]['error'] = null;
      });
    },
    setFieldValue(state, update) {
      if (update.name === 'ordering') {
        return state.ordering.value = update.value;
      }
      state.fields[update.name].value = update.value;
    },
    setFieldError(state, update) {
      if (name === 'ordering') {
        return state.ordering.error = update.error;
      }
      state.fields[update.name].error = update.error;
    },
    highlightField(state, name) {
      if (name === 'ordering') {
        return state.ordering.highlight_field = true;
      }
      state.fields[name].highlight_field = true;
    },
    unhighlightField(state, name) {
      if (name === 'ordering') {
        return state.ordering.highlight_field = false;
      }
      state.fields[name].highlight_field = false;
    },
    highlightExplainer(state, name) {
      if (name === 'ordering') {
        return state.ordering.highlight_explainer = true;
      }
      state.fields[name].highlight_explainer = true;
    },
    unhighlightExplainer(state, name) {
      if (name === 'ordering') {
        return state.ordering.highlight_explainer = false;
      }
      state.fields[name].highlight_explainer = false;
    },
  },
  getters: {
    hitcount: state => state.hitcount,
    page: state => parseInt(state.page),
    cursor: state => state.cursor,
    previous_page_url: state => state.previous_page_url,
    next_page_url: state => state.next_page_url,
    fields: state => state.fields,
    results: state => state.results,
    resultsShown: state => state.resultsShown,
    first_result_number: state => state.first_result_number,
    last_result_number: state => state.last_result_number,
    showLoading: state => state.showLoading,
    page_size: state => state.page_size,
    choices: state => state.choices,
    search_error: state => state.search_error,
    ordering: state => state.ordering,
    urls: state => state.urls,
    api_root: state => state.urls.api_root,
    show_explainer: state => state.show_explainer,
    advanced_fields_shown: state => state.advanced_fields_shown,
    populated_fields(state) {
      let populated = [];
      Object.keys(state.fields).forEach(name => {
        if (state.fields[name]['value']) {
          populated[name] = { ...state.fields[name], ...{'name': name}};
        }
      });
      return populated
    },
    field_name_list(state) {
      return Object.keys(state.fields)
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

      params['ordering'] = state.ordering['value'];

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
      if (name === 'ordering') {
        return !(!state.ordering.error);
      }
      return !(!state.fields[name].error);
    },
    getField: (state) => (name) => {
      if (name === 'ordering') {
        return { ...state.ordering, ...{'name': 'ordering'}}
      }
      return { ...state.fields[name], ...{'name': name}};
    },
    getNewParams: function (state, getters) {
      let new_params = {}
      if (state.cursor) {
        new_params['cursor'] = state.cursor
      }
      if (state.page) {
        new_params['page'] = state.page
      }
      new_params['ordering'] = state.ordering.value;
      Object.keys(getters.populated_fields).forEach(key => {
          new_params[key] = getters.getField(key).value
      });
      return new_params
    },
  },
  actions: {
    resetSearchResults: function ({commit}) {
      commit('hitcount', null);
      commit('page', 1);
      commit('results', []);
      commit('first_result_number', null);
      commit('last_result_number', null);
      commit('clearFieldErrors')
    },
    searchFromParams: function ({dispatch}) {
      dispatch('ingestDataFromQuery', router.currentRoute.query).then(()=> {
        dispatch('executeSearch', {doNotUpdateUrl: true});
      }).catch((error)=>{
        if (error !== "no change") {
            throw error
        }
      });
    },
    searchFromForm: function ({dispatch}) {
      dispatch('executeSearch', {});
    },
    executeSearch: function ({commit, dispatch}, {url=null, doNotUpdateUrl=null}) {
      commit('showLoading', true);
      dispatch('resetSearchResults')

      if (!url) {
        url = this.getters.new_query_url
      }
      Object.keys(this.getters.populated_fields).forEach(field => {
        if (field !== 'search') {
          commit('showAdvanced');
        }
      });
      axios
          .get(url)
          .then(response => {
            return response.data
          })
          .then(results_json => {

          if(!doNotUpdateUrl) {
              dispatch('updateQueryParameters', this.getters.getNewParams)
          }
            commit('hitcount', results_json.count);
            commit('cursor', new URL(url).searchParams.get("cursor"));

            if (results_json.next) {
              commit('next_page_url', results_json.next);
            } else {
              commit('next_page_url', null)
            }

            if (results_json.previous) {
              commit('previous_page_url', results_json.previous)
            } else {
              commit('previous_page_url', null)
            }
            commit('results', results_json.results)
      }).then(() => {

      }).then(() => {
            commit('showLoading', false);
      }).catch(error => {
        commit('showLoading', false);
        if (error.response) { // if we got an error response from the server
          if (error.response.status === 400) {
            // handle field errors
            Object.keys(error.response.data).forEach(field => {
              commit('setFieldError', { 'name': field, 'error': error.response.data[field].join(', ')} )
            });
            return false
          } else {
            commit('search_error', "Error " + error.response.status + "- query failed: " + url);
            return false
          }
        } else if (error.request) { // if the request itself failed
          commit('search_error', "Search error: request failed" + url + " " + error.request);
          return false
        }

        // if something else went wrong
        commit('search_error', "Search error: " + error);
        throw error;
      })
    },
    pageForward: function ({commit, dispatch}) {
      if (this.getters.next_page_url) {
        commit('page', this.getters.page + 1);
        dispatch('executeSearch', {url: this.getters.next_page_url});
      }
    },
    pageBackward: function ({commit, dispatch}) {
      if (this.getters.previous_page_url && this.getters.page > 1) {
        commit('page', this.getters.page - 1);
        dispatch('executeSearch', {url: this.getters.previous_page_url});
      }
    },
    ingestDataFromQuery: function ({commit}, query) {
      return new Promise((resolve, reject) => {
        let change_flag = false;

        if (query['cursor'] && query['cursor'] !== this.state.cursor) {
          change_flag = true;
          commit('cursor', query['cursor'])
        }

        if (query['page'] && query['page'] !== this.state.page) {
          change_flag = true;
          commit('page', query['page'])
        }

        Object.keys(this.state.fields).forEach(key => {
          if (!query[key] && this.state.fields[key].value) {
            change_flag = true;
            commit('clearField', key)
          } else if (query[key] && this.state.fields[key].value !== query[key]) {
            change_flag = true;
            commit('setFieldValue', {'name': key, 'value': query[key]})
          }
        });

        if (change_flag) {
          resolve("updated")
        }

        reject("no change");
      })
    },
    updateQueryParameters: function (commit, params) {
      router.push({name: 'search', query: params}).catch(err => {
        if (err.name !== 'NavigationDuplicated') {
          throw err
        }
      });
    }
  }
});


export default store;