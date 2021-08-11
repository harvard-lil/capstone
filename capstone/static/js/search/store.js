import Vue from 'vue'
import Vuex from 'vuex'
import {encodeQueryData} from "../utils";
import axios from "axios";
import router from './router'

// defined in template
const importUrls = urls; // eslint-disable-line
const importChoices = choices; // eslint-disable-line
const temp_court_list = require("./temp_court_list");

// helpers
function cursorFromUrl(url) {
  if (url)
    return new URL(url).searchParams.get("cursor");
  return null;
}

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
    exposeAuthorCitesToField: false,
    exposeDynamicCitesToField: [],
    last_result_number: null,
    showLoading: false,
    previousPageCursor: null,
    nextPageCursor: null, 
    page_size: 10,
    whitelisted: importChoices.whitelisted,
    search_error: null,
    display_class: '',
    urls: importUrls,
    download_size: 10000,
    download_full_case: true,
    show_explainer: false,
    advanced_fields_shown: false,
    change_dynamic_fields: false,
    fields: {
      search: {
        value: null,
        default_value: null,
        label: "Full-text search",
        placeholder: "Enter keyword or phrase",
        info: "Terms stemmed and combined using AND. Words in quotes searched as phrases.",
        highlight_field: false,
        highlight_explainer: false,
        error: null,
        value_when_searched: null
      },
      decision_date_min: {
        value: null,
        default_value: null,
        label: "Date from YYYY-MM-DD",
        placeholder: "YYYY-MM-DD",
        highlight_field: false,
        highlight_explainer: false,
        error: null,
        value_when_searched: null
      },
      decision_date_max: {
        value: null,
        default_value: null,
        label: "Date to YYYY-MM-DD",
        placeholder: "YYYY-MM-DD",
        highlight_field: false,
        highlight_explainer: false,
        error: null,
        value_when_searched: null
      },
      name_abbreviation: {
        value: null,
        default_value: null,
        label: "Case name abbreviation",
        placeholder: "Enter case name abbreviation e.g. Taylor v. Sprinkle",
        highlight_field: false,
        highlight_explainer: false,
        error: null,
        value_when_searched: null
      },
      docket_number: {
        value: null,
        default_value: null,
        label: "Docket number",
        placeholder: "e.g. Civ. No. 74-289",
        highlight_field: false,
        highlight_explainer: false,
        error: null,
        value_when_searched: null
      },
      reporter: {
        value: [],
        default_value: [],
        label: "Reporter",
        choices: importChoices.reporter.map((element) => { return  {'label': element[1], 'value': element[0].toString() } }),
        highlight_field: false,
        highlight_explainer: false,
        error: null,
        value_when_searched: null
      },
      jurisdiction: {
        value: [],
        default_value: [],
        label: "Jurisdiction",
        choices: importChoices.jurisdiction.map((element) => { return  {'label': element[1], 'value': element[0] } }),
        highlight_field: false,
        highlight_explainer: false,
        error: null,
        value_when_searched: null
      },
      cite: {
        value: null,
        default_value: null,
        label: "Citation e.g. 1 Ill. 17",
        placeholder: "e.g. 1 Ill. 17",
        highlight_field: false,
        highlight_explainer: false,
        error: null,
        value_when_searched: null
      },
      court: {
        value: [],
        default_value: [],
        label: "Court",
        placeholder: "e.g. ill-app-ct",
        choices: temp_court_list.map((element) => { return  {'label': element[1], 'value': element[0] } }),
        highlight_field: false,
        highlight_explainer: false,
        error: null,
        value_when_searched: null
      },
      author: {
        value: null,
        default_value: null,
        label: "Author e.g. breyer",
        placeholder: "e.g. breyer",
        highlight_field: false,
        highlight_explainer: false,
        error: null,
        value_when_searched: null
      },
      author_type: {
        value: null,
        default_value: null,
        label: "Author Type e.g. scalia:dissent",
        placeholder: "e.g. scalia:dissent",
        highlight_field: false,
        highlight_explainer: false,
        error: null,
        value_when_searched: null
      },
      author__cites_to: {
        value: null,
        default_value: null,
        label: "Author opinion cites to e.g. 367 U.S. 643",
        placeholder: "e.g. 367 U.S. 643",
        highlight_field: false,
        highlight_explainer: false,
        error: null,
        value_when_searched: null
      },
      cites_to: {
        value: null,
        default_value: null,
        label: "Case text cites to e.g. 367 U.S. 643",
        placeholder: "e.g. 367 U.S. 643",
        highlight_field: false,
        highlight_explainer: false,
        error: null,
        value_when_searched: null
      },
      cites_to__: {
        value: [],
        default_value: [],
        choices: [],
        label: "Cases that cite to cases...",
        placeholder: "e.g. in a jurisdiction, court, etc.",
        highlight_field: false,
        highlight_explainer: false,
        error: null,
        value_when_searched: null,
        dynamic_field: true,
      },
    },
    ordering: {
      value: "relevance",
      default_value: "relevance",
      label: "Result Sorting",
      choices: [
        {"value": "relevance", "label": "Most Relevant First"},
        {"value": "-decision_date", "label": "Newest Decisions First"},
        {"value": "decision_date", "label": "Oldest Decisions First"}],
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
    download_size(state, value) {
      state.download_size= value;
    },
    download_full_case(state, value) {
      state.download_full_case= value;
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
    nextPageCursor(state, value) {
      state.nextPageCursor = value;
    },
    previousPageCursor(state, value) {
      state.previousPageCursor = value;
    },
    clearFieldandSearch(state, field_name) {
      state.fields[field_name].value = state.fields[field_name].error = null;
      this.dispatch('searchFromForm')
    },
    trimFieldValueArrayandSearch(state, [field_name, value]) {
      state.fields[field_name].value = state.fields[field_name].value.filter(item => item !== value);
      this.dispatch('searchFromForm')
    },
    clearFieldErrors(state) {
      state.ordering.error = null;
      Object.keys(state.fields).forEach(field => {
        state.fields[field]['error'] = null;
      });
    },
    setFieldValue(state, {name, value}) {
      const field = name === 'ordering' ? state.ordering : state.fields[name];
      if (value)
        field.value = value;
      else {
        // if value is false-y, reset field to default
        field.error = null;
        field.value = field.default_value;
      }
    },
    setFieldValueWhenSearched(state, update) {
      if (update.name === 'ordering')
        return
      state.fields[update.name].value_when_searched = update.value;
    },
    setFieldError(state, {name, error}) {
      if (name === 'ordering')
        state.ordering.error = error;
      else if(state.fields[name])
        state.fields[name].error = error;
      else
        state.search_error = error;
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
    exposeFields(state, {field_to_change, value}) {
      if (field_to_change === 'author') {
        return state.exposeAuthorCitesToField = true;
      } else if (field_to_change == 'dynamic') {
        if (!Array.isArray(value)) value = [value];
        const newValue = value.map((key) => { return  {
          'name': `cites_to__${key}`,
          'label': `Citations to ${key}`, 
        }});

        // Only update array on change in order to prevent infinite looping. Otherwise,
        // rendered divs will constantly refresh. Using the filter logic here seemingly 
        // does not resolve the loop.
        const larger = state.exposeDynamicCitesToField.length > newValue.length 
          ? state.exposeDynamicCitesToField.length : newValue.length;
        for (var i = 0; i < larger; ++i) {
          const a = state.exposeDynamicCitesToField[i] ? state.exposeDynamicCitesToField[i].label : 'novalue';
          const b = newValue[i] ? newValue[i].label : 'novalue';
          if (a !== b)  {
            let toDelete = state.exposeDynamicCitesToField.filter(x => !newValue.includes(x));
            for (let object of toDelete) {
              state.fields[object['name']].value = null;
              state.fields[object['name']].value_when_searched = null;
            }

            state.exposeDynamicCitesToField = newValue;
          }
        }
      }
    }
  },
  getters: {
    hitcount: state => state.hitcount,
    page: state => parseInt(state.page),
    cursor: state => state.cursor,
    previousPageCursor: state => state.previousPageCursor,
    nextPageCursor: state => state.nextPageCursor,
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
    exposeAuthorCitesToField: state => state.exposeAuthorCitesToField,
    getExposeDynamicCitesToField: state => state.exposeDynamicCitesToField,
    urls: state => state.urls,
    api_root: state => state.urls.api_root,
    download_size: state => state.download_size,
    download_full_case: state => state.download_size,
    show_explainer: state => state.show_explainer,
    advanced_fields_shown: state => state.advanced_fields_shown,
    populated_fields(state) {
      let populated = {};
      Object.keys(state.fields).forEach(name => {
        if (state.fields[name]['value']) {
          populated[name] = { ...state.fields[name], ...{'name': name}};
        }
      });
      return populated
    },
    populated_fields_during_search(state) {
      let populated = {};
      Object.keys(state.fields).forEach(name => {
        if (state.fields[name]['value_when_searched'] && state.fields[name]['value_when_searched'].length > 0) {
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

      if (state.cursor) {
        params['cursor'] = state.cursor
      }

      params['ordering'] = state.ordering['value'];

      return `${state.urls.api_root}cases/?${encodeQueryData(params, true)}`;
    },
    download_url: (state) => (download_format) => {
      /* assembles and returns URL */
      const params = {};

      // build the query parameters using the form fields
      Object.keys(state.fields).forEach(key => {
        if (state.fields[key]['value']) {
          params[key] = state.fields[key]['value'];
        }
      });

      params['format'] = download_format;
      params['full_case'] = state.download_full_case ? 'true' : 'false';
      params['page_size'] = state.download_size;

      return `${state.urls.api_root}cases/?${encodeQueryData(params, true)}`;
    },
    trends_link: (state) => {
      var params = '';
      for (const key in state.fields) {
        if (key === 'cites_to__') continue;
        var value = state.fields[key].value;
        if (value && value.length > 0) {
          if (Array.isArray(value)) {
            for (const item of value) {
              params += encodeURIComponent(key + '=' + item + '&');
            }
          } else {
            params += encodeURIComponent(key + '=' + value + '&');
          }
        } 
      }

      return state.urls.trends + '?q=api(' + params.slice(0, -3) + ')'
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
      let new_params = {};
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
    getLabelForChoice: (state, getters) => (field_name, value) => {
      let field = getters.getField(field_name);
      return field.choices.filter(item => item.value === value)[0].label;
    },
  },
  actions: {
    clearSearchMeta: function({commit}) {
      commit('page', 1);
      commit('first_result_number', null);
      commit('last_result_number', null);
      commit('cursor', null);
    },
    resetSearchResults: function ({commit}) {
      commit('hitcount', null);
      commit('results', []);
      commit('clearFieldErrors')
    },
    searchFromForm: function ({dispatch}) {
      dispatch('clearSearchMeta', {});
      dispatch('pushUrlUpdate');
    },
    async searchFromParams ({commit, dispatch, getters}) {
      await dispatch('ingestDataFromQuery', router.currentRoute.query);

      if (!router.currentRoute.query.page)
        return;

      commit('showLoading', true);
      await dispatch('resetSearchResults');
      const url = getters.new_query_url;

      // expand advanced fields if any are set
      for (let field in getters.populated_fields) {
        if (field !== 'search') {
          commit('showAdvanced');
          break;
        }
      }

      try {
        const response = await axios.get(url);
        const results_json = await response.data;
        commit('hitcount', results_json.count);
        for (let field of Object.keys(getters.fields)) {
          commit('setFieldValueWhenSearched', getters.getField(field))
        }
        commit('nextPageCursor', cursorFromUrl(results_json.next));
        commit('previousPageCursor', cursorFromUrl(results_json.previous));
        commit('results', results_json.results);
        commit('showLoading', false);
      } catch(error) {
        commit('showLoading', false);
        if (error.response) { // if we got an error response from the server
          if (error.response.status === 400) {
            // handle field errors
            Object.keys(error.response.data).forEach(field => {
              commit('setFieldError', {'name': field, 'error': error.response.data[field].join(', ')})
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
      }
    },
    pageForward: function ({commit, dispatch, getters}) {
      if (getters.nextPageCursor) {
        commit('page', getters.page + 1);
        commit('cursor', getters.nextPageCursor);
        dispatch('pushUrlUpdate');
      }
    },
    pageBackward: function ({commit, dispatch, getters}) {
      if (getters.previousPageCursor && getters.page > 1) {
        commit('page', getters.page - 1);
        commit('cursor', getters.page > 1 ? getters.previousPageCursor : null);
        dispatch('pushUrlUpdate');
      }
    },
    ingestDataFromQuery ({commit}, query) {
      // Update state based on query string
      commit('cursor', query.cursor || null);
      commit('page', query.page || null);
      commit('setFieldValue', {'name': 'ordering', 'value': query.ordering || null});
      for (const field_name of Object.keys(this.state.fields)) {
        commit('setFieldValue', {'name': field_name, 'value': query[field_name] || null});
      }
    },
    pushUrlUpdate: function ({getters}) {
      router.push({name: 'search', query: getters.getNewParams}).catch(err => {
        if (err.name !== 'NavigationDuplicated') {
          throw err
        }
      });
    }
  }
});

// Seed store with cites_to__ field dynamically
store.state.fields['cites_to__'].choices = Object.keys(store.state.fields).filter(key => !key.includes('cites_to'))
  .map((key) => { return  {'label': key, 'value': key }})

for (const key of Object.keys(store.state.fields)) {
  if (key !== "cites_to__") {
    Vue.set(store.state.fields, `cites_to__${key}`, {
      value: null,
      default_value: null,
      label: `Citations to ${key}`,
      placeholder: "",
      highlight_field: false,
      highlight_explainer: false,
      error: null,
      value_when_searched: null            
    });
  }
}

export default store;
