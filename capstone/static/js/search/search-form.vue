<template>

  <form @submit.prevent="$emit('new-search', fields, endpoint)" class="row">
    <div class="col-md-3">
      <h1 class="page-title">
        <img alt=""
             aria-hidden="true"
             :src='`${urls.static}img/arrows/violet-arrow-right.svg`'
             class="decorative-arrow"/>
        Find
      </h1>
    </div>
    <div class="col-md-9">
      <div class="row">
        <div class="col-lg-7">

          <searchroutes :endpoint="endpoint" :endpoints="endpoints">
          </searchroutes>
          <br/>
          <!-- Table showing search fields. Also includes add field and search buttons. -->
          <div v-if="search_error"
               role="alert"
               class="alert alert-danger">
            <p>{{search_error}}</p>
            <h2 id="form-errors-heading" tabindex="-1" class="sr-only">{{search_error}}</h2>
          </div>
          <div v-if="Object.keys(field_errors).length"
               role="alert"
               class="alert alert-danger">
            <!--<p>Please correct the following <strong>2 error(s)</strong>: </p>-->
            <p>Please correct the following {{ Object.keys(field_errors).length }} error(s):</p>
            <h2 id="form-errors-heading" tabindex="-1" class="sr-only">
              Please correct the following {{Object.keys(field_errors).length}} error(s)</h2>
            <ul class="bullets">
              <li v-for="(error, name) in field_errors"
                  :key="'error' + name">
                <a :href="'#'+name">{{getFieldByName(name).label}}:</a> {{error}}
              </li>
            </ul>
          </div>
          <div class="row field-row"
               v-for="field in fields" :key="field.name"
               v-bind:class="{ 'alert-danger': field_errors.hasOwnProperty(field['name']) }"
               @mouseover="highlightExplainer"
               @mouseout="unhighlightExplainer">
            <div class="col-4 field_label_container">
              <label class="querylabel" :for="field['name']">
                {{ field["label"] }}
              </label>
            </div>
            <div class="col-7">
              <template v-if="field['choices']">
                <select v-model='field["value"]'
                        :id='field["name"]'
                        @change="valueUpdated"
                        @focus="highlightExplainer"
                        @blur="unhighlightExplainer">
                  <option v-for="choice in choices[field['choices']]"
                          :value="choice[0]" v-bind:key="choice[1]">
                    {{choice[1]}}
                  </option>
                </select>
              </template>
              <template v-else>
                <input v-model='field["value"]'
                       :class="['queryfield', field_errors[field.name] ? 'is-invalid' : '']"
                       type="text"
                       :id='field["name"]'
                       :placeholder='field["format"] || false'
                       v-on:keyup="valueUpdated"
                       @focus="highlightExplainer"
                       @blur="unhighlightExplainer">
              </template>
              <small v-if="field.info" :id="`help-text-${field.name}`" class="form-text text-muted">{{field.info}}
              </small>
              <div v-if="field_errors[field.name]" class="invalid-feedback">
                {{ field_errors[field.name] }}
              </div>
            </div>
            <div class="col-1">
              <button type="button"
                      :class="[fields.length <= 1 ? 'disabled' : 'active', 'field-button']"
                      :disabled="fields.length <= 1"
                      @click="removeField(field.name)">
              </button>
            </div>
          </div>
          <!--Buttons row-->
          <div class="row">
            <div class="col-3"></div>
            <div class="col-8">
              <div class="submit-button-group">
                <loading-button :showLoading="showLoading">Search</loading-button>
              </div>
              <div v-if="fields.length > 0" class="dropdown addfield">
                <button class="dropdown-toggle add-field-button btn-secondary"
                        type="button"
                        id="dropdownMenuButton"
                        data-toggle="dropdown"
                        aria-haspopup="true"
                        aria-expanded="false">
                  Add Field&nbsp;
                </button>
                <div class="dropdown-menu" aria-labelledby="dropdownMenuButton">
                  <button class="dropdown-item" type="button"
                          v-for="newfield in availableFields()" :key="newfield.name"
                          @click="addField(newfield)">
                    {{ newfield.label }}
                  </button>
                </div>
              </div>

            </div>
            <div class="col-1"></div>
          </div>
          <div class="row">
            <div class="col-3"></div>
            <div class="col-8">
              <div class="submit-button-group">
                <button id="query-explainer-button" class="mt-0" @click="toggleExplainer"
                        v-if="show_explainer === true">HIDE API CALL
                </button>
                <button id="query-explainer-button" class="mt-0" @click="toggleExplainer" v-else>SHOW API CALL</button>
              </div>
            </div>
            <div class="col-1"></div>
          </div>

        </div>
        <div class="col-lg-5 search-disclaimer">
          <p>
            Searching U.S. caselaw published through mid-2018. <a :href="urls.search_docs">Documentation</a>.<br>
          </p>
          <p>
            <span class="bold">Need legal advice?</span> This is not your best option! Read about
            <a :href="urls.search_docs + '#research'">our limitations and alternatives</a>.
          </p>
        </div>
      </div>
    </div>
    <div class="col-9 offset-3 query-explainer" v-show="show_explainer">
      <div class="row">
        <div class="col-12">
          <small id="help-text-search" class="form-text text-muted">
            Hover over input boxes or url segments to expose their counterpart in your search query.
          </small>
        </div>
      </div>
      <div class="row">
        <div class="col-12 p-3 url-block">
          <query-explainer :query_url="query_url"></query-explainer>
        </div>
      </div>
    </div>
  </form>
</template>
<script>
  import searchroutes from "./search-routes"
  import LoadingButton from '../vue-shared/loading-button.vue';
  import QueryExplainer from './query-explainer';

  export default {
    components: {searchroutes, LoadingButton, QueryExplainer},
    data: function () {
      return {
        query: [],
        newfield: null,
        page_size: 10,
        fields: [],
        query_url: '',
        show_explainer: false,
        endpoints: {
          cases: [
            {
              name: "search",
              value: "",
              label: "Full-Text Search",
              default: true,
              format: "e.g. library",
              info: "Terms stemmed and combined using AND. Words in quotes searched as phrases."
            },
            {
              name: "ordering",
              value: "relevance",
              label: "Result Sorting",
              choices: 'sort',
            },
            {
              name: "name_abbreviation",
              label: "Case Name Abbreviation",
              value: "",
              format: "e.g. Taylor v. Sprinkle",
            },
            {
              name: "decision_date_min",
              label: "Decision Date Earliest",
              format: "YYYY-MM-DD",
            },
            {
              name: "decision_date_max",
              value: "",
              label: "Decision Date Latest",
              format: "YYYY-MM-DD",
            },
            {
              name: "docket_number",
              value: "",
              label: "Docket Number",
              format: "e.g. Civ. No. 74-289",
            },
            {
              name: "cite",
              value: "",
              label: "Citation",
              format: "e.g. 1 Ill. 17",
            },
            {
              name: "reporter",
              value: "",
              label: "Reporter",
              choices: 'reporter',
            },
            {
              name: "court",
              value: "",
              label: "Court",
              format: "e.g. ill-app-ct",
              hidden: true,
            },
            {
              name: "court_id",
              value: "",
              label: "Court ID",
              format: ""
            },
            {
              name: "jurisdiction",
              value: "",
              label: "Jurisdiction",
              choices: 'jurisdiction',
            }
          ],
          courts: [
            {
              name: "id",
              value: "",
              label: "ID",
              format: ""
            },
            {
              name: "slug",
              value: "",
              label: "Slug",
              format: "e.g. ill-app-ct",
            },
            {
              name: "name",
              value: "",
              label: "Name",
              format: "e.g. 'Illinois Supreme Court'",
            },
            {
              name: "name_abbreviation",
              value: "",
              format: "e.g. 'Ill.'",
              label: "Name Abbreviation",
            },
            {
              name: "jurisdiction",
              value: "",
              label: "Jurisdiction",
              choices: 'jurisdiction',
              default: true,
            }
          ],
          jurisdictions: [
            {
              name: "id",
              value: "",
              format: "e.g. 47",
              label: "Database ID",
            },
            {
              name: "name",
              value: "",
              label: "Name",
              format: "e.g. 'Ill.'",
            },
            {
              name: "name_long",
              value: "",
              label: "Long Name",
              format: "e.g. 'Illinois'",
              default: true,
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
              format: "e.g. 'Illinois Appellate Court Reports'",
            },
            {
              name: "short_name",
              value: "",
              label: "Short Name",
              format: "e.g. 'Ill. App.'",
            },
            {
              name: "start_year",
              value: "",
              label: "Start Year",
              format: "e.g. '1893'",
              info: "Year in which the reporter began publishing."
            },
            {
              name: "end_year",
              value: "",
              label: "End Year",
              format: "e.g. '1894'",
              info: "Year in which the reporter stopped publishing."
            },
            {
              name: "jurisdiction",
              value: "",
              label: "Jurisdiction",
              choices: 'jurisdiction',
              default: true,
            }
          ]
        },

      }
    },
    watch: {
      fields() {
        this.valueUpdated()
      }
    },
    props: ['choices', 'search_error', 'field_errors', 'urls', 'showLoading', 'endpoint'],
    methods: {
      valueUpdated() {
        this.query_url = this.$parent.assembleUrl();
      },
      removeField(field_name) {
        this.fields = this.fields.filter(field => field.name !== field_name);
      },
      addField(field) {
        this.fields.push(field);
      },
      getFieldByName(field_name) {
        return this.endpoints[this.endpoint].find(field => field.name === field_name);
      },
      availableFields() {
        /*
          Return list of fields that can be added for current endpoint, and aren't yet included.
          Fields with hidden=true are excluded.
        */
        return this.endpoints[this.endpoint].filter(field => !field.hidden && !this.fields.includes(field));
      },
      highlightExplainer(event) {
        var explainer_argument = document.getElementById("p_" + event.target.id);
        if (explainer_argument) {
          explainer_argument.classList.add('highlight-parameter');
        }
      },
      unhighlightExplainer(event) {
        var explainer_argument = document.getElementById("p_" + event.target.id);
        if (explainer_argument) {
          explainer_argument.classList.remove('highlight-parameter');
        }
      },
      toggleExplainer() {
        this.show_explainer = this.show_explainer ? false : true
      },
    }
  }
</script>
