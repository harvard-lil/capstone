<template>
  <form @submit.prevent="$emit('new-search', fields, endpoint)" class="row">
    <div class="col-2"></div>
    <div class="col-10 search-form-contents">
      <div class="row">
        <div class="search-form-container">
          <searchroutes :endpoint="endpoint" :endpoints="endpoints">
          </searchroutes>
          <br/>
          <!-- Table showing search fields. Also includes add field and search buttons. -->
          <div class="row">
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
            <div class="col-12">
              <div class="row field_row_container"
                   v-for="field in fields" :key="field.name"
                   v-bind:class="{ 'alert-danger': field_errors.hasOwnProperty(field['name']) }">
                <div class="col-3 field_label_container">
                  <label class="querylabel" :for="field['name']">
                    {{ field["label"] }}
                  </label>
                </div>
                <div class="col-7">
                  <template v-if="field['choices']">
                    <select v-model='field["value"]'
                            :id='field["name"]'>
                      <option v-for="(label, value) in choices[field['choices']]"
                              :value="value" v-bind:key="label">
                        {{label}}
                      </option>
                    </select>
                  </template>
                  <template v-else>
                    <input v-model='field["value"]'
                           :class="['queryfield', field_errors[field.name] ? 'is-invalid' : '']"
                           type="text"
                           :id='field["name"]'
                           :placeholder='field["format"] || false'
                    >
                    <div vif="field_errors[field.name]" class="invalid-feedback">
                      {{ field_errors[field.name] }}
                    </div>
                  </template>
                </div>
                <div class="col-1">
                  <div class="remfield">
                    <button type="button"
                            :class="[fields.length <= 1 ? 'disabled' : 'active', 'field-button']"
                            :disabled="fields.length <= 1"
                            @click="removeField(field.name)">
                    </button>
                  </div>

                </div>
              </div>
              <!--Add field row-->
              <div class="row">
                <div class="col-3"></div>
                <div class="col-7">
                  <div v-if="fields.length > 0" class="dropdown addfield">
                    <button class="dropdown-toggle add-field-button btn-white-violet"
                            type="button"
                            id="dropdownMenuButton"
                            data-toggle="dropdown"
                            aria-haspopup="true"
                            aria-expanded="false">
                      Add Field
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
              <!--Submit row-->
              <div class="row">
                <div class="col-4"></div>
                <div class="col-7">
                  <button class="btn-default btn-submit"
                          type="submit"
                          value="Search">
                    Search
                    <span v-if="show_loading"
                          class="spinner-border spinner-border-sm"
                          role="status"
                          aria-hidden="true"></span>
                  </button>
                  <span v-if="show_loading"
                        id="searching-focus"
                        class="sr-only"
                        tabindex="-1">Searching&nbsp;</span>
                </div>
                <div class="col-1"></div>
              </div>
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
          <hr/>
          <p>
            * Note on full text search:
            Terms will be stemmed and combined using AND. Words in quotes will be searched as a phrase.
          </p>
          <br/>
        </div>
      </div>
    </div>
  </form>
</template>
<script>
  import searchroutes from "./search-routes"

  export default {
    components: {searchroutes},
    data: function () {
      return {
        query: [],
        newfield: null,
        page_size: 10,
        fields: [],
        endpoints: {
          cases: [
            {
              name: "search",
              value: "",
              label: "Full-Text Search",
              default: true,
              format: "e.g. insurance illinois",
              info: ""
            },
            {
              name: "name_abbreviation",
              label: "Case Name Abbreviation",
              value: "",
              format: "e.g. Taylor v. Sprinkle",
              info: "the abbreviated case name"
            },
            {
              name: "decision_date_min",
              label: "Decision Date Earliest",
              format: "YYYY-MM-DD",
              info: "the earliest date on which your results could have been decided"
            },
            {
              name: "decision_date_max",
              value: "",
              label: "Decision Date Latest",
              format: "YYYY-MM-DD",
              info: "the latest date on which your results could have been decided"
            },
            {
              name: "docket_number",
              value: "",
              label: "Docket Number",
              format: "e.g. Civ. No. 74-289",
              info: "the docket number assigned by the court"
            },
            {
              name: "citation",
              value: "",
              label: "Citation",
              format: "e.g. 1 Ill. 17",
              info: "the case citation"
            },
            {
              name: "reporter",
              value: "",
              label: "Reporter",
              choices: 'reporter',
              info: ""
            },
            {
              name: "court",
              value: "",
              label: "Court",
              format: "e.g. ill-app-ct",
              info: "",
              hidden: true,
            },
            {
              name: "jurisdiction",
              value: "",
              label: "Jurisdiction",
              choices: 'jurisdiction',
              info: ""
            }
          ],
          courts: [
            {
              name: "slug",
              value: "",
              label: "Slug",
              format: "e.g. ill-app-ct",
              info: "A slug is a unique alphanumeric identifier which is more readable than a numeric ID."
            },
            {
              name: "name",
              value: "",
              label: "Name",
              format: "e.g. 'Illinois Supreme Court'",
              info: "the official full court name"
            },
            {
              name: "name_abbreviation",
              value: "",
              format: "e.g. 'Ill.'",
              label: "Name Abbreviation",
              info: "the abbreviated court name"
            },
            {
              name: "jurisdiction",
              value: "",
              label: "Jurisdiction",
              choices: 'jurisdiction',
              default: true,
              info: "the court's jurisdiction"
            }
          ],
          jurisdictions: [
            {
              name: "id",
              value: "",
              format: "e.g. 47",
              label: "Database ID",
              info: "A slug is a unique string that represents a database entry which is more readable than a numeric ID."
            },
            {
              name: "name",
              value: "",
              label: "Name",
              format: "e.g. 'Ill.'",
              info: "the short, official name of the jurisdiction"
            },
            {
              name: "name_long",
              value: "",
              label: "Long Name",
              format: "e.g. 'Illinois'",
              default: true,
              info: "the long, official name of the jurisdiction"
            },
            {
              name: "whitelisted",
              value: "",
              label: "Whitelisted Jurisdiction",
              choices: 'whitelisted',
              info: "Whitelisted cases are not subject to the 500 case per day access limitation."
            }
          ],
          reporters: [
            {
              name: "full_name",
              value: "",
              label: "Full Name",
              format: "e.g. 'Illinois Appellate Court Reports'",
              info: "the full reporter name"
            },
            {
              name: "short_name",
              value: "",
              label: "Short Name",
              format: "e.g. 'Ill. App.'",
              info: "the short reporter name"
            },
            {
              name: "start_year",
              value: "",
              label: "Start Year",
              format: "e.g. '1893'",
              info: "the year in which the reporter began publishing"
            },
            {
              name: "end_year",
              value: "",
              label: "End Year",
              format: "e.g. '1894'",
              info: "the year in which the reporter stopped publishing"
            },
            {
              name: "jurisdiction",
              value: "",
              label: "Jurisdiction",
              choices: 'jurisdiction',
              default: true,
              info: "the reporter's jurisdiction"
            }
          ]
        },

      }
    },
    props: ['choices', 'search_error', 'field_errors', 'urls', 'show_loading', 'endpoint'],
    methods: {
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
      }
    }
  }
</script>
