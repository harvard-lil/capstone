<template>
  <form @submit.prevent="$emit('new-search', fields, endpoint)"
        class="row">
    <div class="col-centered col-9">
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
      <!--Fields-->
      <div class="search-fields row">
        <div v-for="(field, index) in fields" :key="field.name" class="col-12">
          <div v-if="field['choices']" class="dropdown dropdown-field">
            <button class="btn dropdown-toggle dropdown-title"
                    type="button"
                    :id="field.name"
                    data-toggle="dropdown"
                    aria-haspopup="true"
                    aria-expanded="false"
                    :aria-describedby="field.label"
                    @focus="highlightExplainer"
                    @blur="unhighlightExplainer">
              {{ field.display_value ? field.display_value : field.label }}
            </button>

            <div class="dropdown-menu" :aria-labelledby="field.name">
              <!-- Include reset field -->
              <a class="dropdown-item reset-field"
                 v-if="field.display_value"
                  @click="updateDropdownVal(index, ['', ''])">
                Reset field</a>
              <!-- Choice fields -->
              <a v-for="choice in choices[field['choices']]" v-bind:key="choice[0]"
                 @click="updateDropdownVal(index, choice)"
                 :class="['dropdown-item', 'search-tab', field.name===choice[0] ? 'active' : '']">
                {{ choice[1] }}
              </a>
            </div>
          </div>

          <textarea v-else-if="field.type === 'textarea'"
                    :aria-label="field.name"
                    v-model="field.value"
                    :class="['queryfield', field_errors[field.name] ? 'is-invalid' : '', 'col-12' ]"
                    :id='field["name"]'
                    :placeholder='field["placeholder"] || false'
                    class="form-control"
                    v-on:keyup="valueUpdated"
                    @focus="highlightExplainer"
                    @blur="unhighlightExplainer">
        </textarea>
          <!-- for text, numbers, and everything else (that we presume is text) -->
          <div v-else class="form-label-group">
            <input v-model='field.value'
                   :aria-label="field.name"
                   :class="['queryfield', field_errors[field.name] ? 'is-invalid' : '', 'col-12' ]"
                   :type='field.type'
                   :placeholder="field.label"
                   :id="field.name"
                   :min="field.min"
                   :max="field.max"
                   @input="valueUpdated"
                   @focus="highlightExplainer"
                   @blur="unhighlightExplainer">
            <label :for="field.name">{{ field.label }}</label>

          </div>
          <div v-if="field_errors[field.name]" class="invalid-feedback">
            {{ field_errors[field.name] }}
          </div>
          <small v-if="field.info"
                 :id="`help-text-${field.name}`"
                 class="form-text text-muted">
            {{ field.info }}
          </small>
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
          <div class="col-12 url-block">
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
            label: "Result sorting",
            choices: 'sort',
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
            name: "cite",
            value: "",
            label: "Citation e.g. 1 Ill. 17",
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
            label: "Slug e.g. ill-app-ct",
            placeholder: "e.g. ill-app-ct",
          },
          {
            name: "name",
            value: "",
            label: "Name e.g. 'Illinois Supreme Court'",
            placeholder: "e.g. 'Illinois Supreme Court'",
          },
          {
            name: "name_abbreviation",
            value: "",
            placeholder: "e.g. 'Ill.'",
            label: "Name abbreviation e.g. 'Ill.'",
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
  props: [
    'choices',
    'search_error',
    'field_errors',
    'urls',
    'showLoading',
    'endpoint'],
  methods: {
    valueUpdated() {
      this.query_url = this.$parent.assembleUrl();
    },
    updateDropdownVal(index, choice) {
      this.fields[index].value = choice[0];
      this.fields[index].display_value = choice[1];
      this.valueUpdated()
    },
    getFieldByName(field_name) {
      return this.endpoints[this.endpoint].find(field => field.name === field_name);
    },
    changeEndpoint: function (new_endpoint) {
      this.$emit('update:endpoint', new_endpoint)
      this.fields = this.endpoints[new_endpoint];
      this.valueUpdated();
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
    },
    downloadResults: function (format) {
      return this.$parent.assembleUrl() + "&format=" + format;
    }
  },
  mounted() {
    this.valueUpdated();
  }
}
</script>
