<template>
  <form @submit.prevent="$emit('new-search', fields, endpoint)"
        class="col-centered col-9">
    <div class="col-md-2 empty-push-div"></div>
    <div class="col-md-10 title-container">
      <h3 class="page-title">
        <img alt="" aria-hidden="true"
             src="{% static 'img/arrows/violet-arrow-right.svg' %}"
             class="decorative-arrow"/>
        Search
      </h3>
    </div>
    <div class="row">
      <div class="dropdown dropdown-search-routes">
        <button class="btn dropdown-toggle dropdown-title"
                type="button"
                id="search-routes-dropdown"
                data-toggle="dropdown"
                aria-haspopup="true"
                aria-expanded="false"
                :aria-describedby="endpoint">
          {{ endpoint }}
        </button>

        <div class="dropdown-menu" aria-labelledby="search-routes-dropdown">
          <a v-for="current_endpoint in Object.keys(endpoints)" :key="current_endpoint"
             @click="changeEndpoint(current_endpoint)"
             :class="['dropdown-item', 'search-tab', current_endpoint===endpoint ? 'active' : '']">
            {{ current_endpoint }}
          </a>
        </div>
      </div>
    </div>

    <!-- Table showing search fields. Also includes add field and search buttons. -->
    <div v-if="search_error"
         role="alert"
         class="alert alert-danger">
      <p>{{ search_error }}</p>
      <h2 id="form-errors-heading" tabindex="-1" class="sr-only">{{ search_error }}</h2>
    </div>
    <div v-if="Object.keys(field_errors).length"
         role="alert"
         class="alert alert-danger">
      <!--<p>Please correct the following <strong>2 error(s)</strong>: </p>-->
      <p>Please correct the following {{ Object.keys(field_errors).length }} error(s):</p>
      <h2 id="form-errors-heading" tabindex="-1" class="sr-only">
        Please correct the following {{ Object.keys(field_errors).length }} error(s)</h2>
      <ul class="bullets">
        <li v-for="(error, name) in field_errors"
            :key="'error' + name">
          <a :href="'#'+name">{{ getFieldByName(name).label }}:</a> {{ error }}
        </li>
      </ul>
    </div>
    <div v-for="field in fields" :key="field.name" class="row">
      <small v-if="field.info" :id="`help-text-${field.name}`" class="form-text text-muted">{{ field.info }}
      </small>
      <template v-if="field['choices']">
        <select v-model='field["value"]'
                :id='field["name"]'
                class="form-control"
                @change="valueUpdated"
                @focus="highlightExplainer"
                @blur="unhighlightExplainer">
          <option selected hidden value="">{{ field.label }}</option>
          <option v-for="choice in choices[field['choices']]"
                  :value="choice[0]" v-bind:key="choice[0]">
            {{ choice[1] }}
          </option>
        </select>
      </template>
      <template v-else-if="Array.isArray(field)">
        <div class="form-inline input-group">
          <div v-for="subfield in field" :key="subfield.name"
               class="col-6">
            <input :type="subfield.type" class="queryfield"
                   :aria-label="subfield.name"
                   v-model='subfield["value"]'
                   v-on:keypress="valueUpdated"
                   @focus="highlightExplainer"
                   @blur="unhighlightExplainer"
                   aria-describedby="basic-addon1">
          </div>
        </div>
      </template>
      <template v-else>
        <div v-if="field.type === 'date'" class="input-group mb-3 col-6">
<!--    <div class="form-label-group">-->
<!--      <input type="email" id="inputEmail" class="form-control" placeholder="Email address" required autofocus>-->
<!--      <label for="inputEmail">Email address</label>-->
<!--    </div>-->

          <input type="date" class="form-control"
                 :aria-label="field.name"
                 v-model='field["value"]'
                 v-on:keypress="valueUpdated"
                 @focus="highlightExplainer"
                 @blur="unhighlightExplainer"
                 aria-describedby="basic-addon1">
        </div>
        <!-- for text, numbers, and everything else (that we presume is text) -->
        <div v-if="field.type === 'text' || field.type === 'number' || !field.type"
             class="col-12 form-label-group">
          <input v-model='field.value'
                 :class="['queryfield', field_errors[field.name] ? 'is-invalid' : '', 'col-12' ]"
                 :type='field.type'
                 :placeholder="field.label"
                 :id="field.name"
                 :min="field.min"
                 :max="field.max"
                 v-on:keyup="valueUpdated"
                 @focus="highlightExplainer"
                 @blur="unhighlightExplainer">
          <label :for="field.name">{{field.label}}</label>
        </div>
        <textarea v-if="field.type === 'textarea'"
                  :class="['queryfield', field_errors[field.name] ? 'is-invalid' : '', 'col-12' ]"
                  :type='field["type"]' :id='field["name"]'
                  :placeholder='field["placeholder"] || false'
                  class="form-control"
                  v-on:keyup="valueUpdated"
                  @focus="highlightExplainer"
                  @blur="unhighlightExplainer">
        </textarea>
      </template>


      <div v-if="field_errors[field.name]" class="invalid-feedback">
        {{ field_errors[field.name] }}
      </div>
    </div>
    <!--Buttons row-->

    <div class="submit-button-group">
      <search-button :showLoading="showLoading" :endpoint="endpoint"></search-button>
      <a href="#" id="query-explainer-button" class="mt-0" @click="toggleExplainer"
         v-if="show_explainer">HIDE API CALL
      </a>
      <a href="#" id="query-explainer-button" class="mt-0" @click="toggleExplainer" v-else>SHOW API CALL</a>
    </div>
    <div class="query-explainer" v-show="show_explainer">
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
    <div class="search-disclaimer">
      <p>
        Searching U.S. caselaw published through mid-2018. <a :href="urls.search_docs">Documentation</a>.<br>
      </p>
      <p>
        <span class="bold">Need legal advice?</span> This is not your best option! Read about
        <a :href="urls.search_docs + '#research'">our limitations and alternatives</a>.
      </p>
    </div>
  </form>
</template>
<script>
import SearchButton from '../vue-shared/search-button.vue';
import QueryExplainer from './query-explainer';

export default {
  components: {SearchButton, QueryExplainer},
  data: function () {
    return {
      query: [],
      // newfield: null,
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
            type: "textarea",
            placeholder: "Enter keyword or phrase",
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
            placeholder: "Enter case name abbreviation e.g. Taylor v. Sprinkle",
          },
          [{
            name: "decision_date_min",
            label: "Decision Date Earliest",
            placeholder: "YYYY-MM-DD",
            type: "date",
          },
            {
              name: "decision_date_max",
              value: "",
              label: "Decision Date Latest",
              placeholder: "YYYY-MM-DD",
              type: "date",
            }],
          {
            name: "docket_number",
            value: "",
            label: "Docket Number",
            placeholder: "e.g. Civ. No. 74-289",
          },
          {
            name: "cite",
            value: "",
            label: "Citation",
            placeholder: "e.g. 1 Ill. 17",
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
            placeholder: "e.g. ill-app-ct",
            hidden: true,
          },
          {
            name: "court_id",
            value: "",
            label: "Court ID",
            placeholder: ""
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
            placeholder: ""
          },
          {
            name: "slug",
            value: "",
            label: "Slug",
            placeholder: "e.g. ill-app-ct",
          },
          {
            name: "name",
            value: "",
            label: "Name",
            placeholder: "e.g. 'Illinois Supreme Court'",
          },
          {
            name: "name_abbreviation",
            value: "",
            placeholder: "e.g. 'Ill.'",
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
            placeholder: "e.g. 47",
            label: "Database ID",
          },
          {
            name: "name",
            value: "",
            label: "Name",
            placeholder: "e.g. 'Ill.'",
          },
          {
            name: "name_long",
            value: "",
            label: "Long Name",
            placeholder: "e.g. 'Illinois'",
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
            placeholder: "e.g. 'Illinois Appellate Court Reports'",
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
    // fields() {
    //   console.log("watching fields", this.fields)
    //   this.valueUpdated()
    // }

  },
  props: [
    'choices',
    'search_error',
    'field_errors',
    'urls',
    'showLoading',
    'endpoint'],
  methods: {
    valueUpdated() {
      console.log("valueUpdated")
      // this.query_url = this.$parent.assembleUrl();
    },
    getFieldByName(field_name) {
      return this.endpoints[this.endpoint].find(field => field.name === field_name);
    },
    changeEndpoint: function (new_endpoint) {
      // this.endpoint = new_endpoint;
      this.$emit('update:endpoint', new_endpoint)
      // this.$parent.endpoint = this.endpoint;
      this.fields = this.endpoints[new_endpoint];
      console.log("changeEndpoint", new_endpoint)
    },
    highlightExplainer(event) {
      let explainer_argument = document.getElementById("p_" + event.target.id);
      if (explainer_argument) {
        explainer_argument.classList.add('highlight-parameter');
      }
    },
    unhighlightExplainer(event) {
      let explainer_argument = document.getElementById("p_" + event.target.id);
      if (explainer_argument) {
        explainer_argument.classList.remove('highlight-parameter');
      }
    },
    toggleExplainer() {
      this.show_explainer = !this.show_explainer;
      console.log("show explainer", this.show_explainer)
    },
    downloadResults: function (format) {
      return this.$parent.assembleUrl() + "&format=" + format;
    }
  }
}
</script>
