<template>
  <form @submit.prevent="$emit('new-search', fields, endpoint)">
    <div class="search-form-container col-centered">
      <searchroutes :endpoint="endpoint"></searchroutes>
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
          <h2 id="form-errors-heading" tabindex="-1" class="sr-only">Please correct the following {{ Object.keys(field_errors).length }} error(s)</h2>
          <ul class="bullets">
            <li v-for="(error, name) in field_errors"
                :key="'error' + name">
              <a :href="'#'+name">{{getFieldEntry(name, endpoint).label}}:</a> {{error}}
            </li>
          </ul>
        </div>
        <div class="col-12">
          <div class="row field_row_container"
               v-for="field in fields"
               v-bind:key="field['name']"
               v-bind:class="{ 'alert-danger': field_errors.hasOwnProperty(field['name']) }">
            <div class="col-4 field_label_container">
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
              <template>
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
                        @click="removeField(field['name'])">
                </button>
              </div>

            </div>
          </div>
          <!--Add field row-->
          <div class="row">
            <div class="col-4"></div>
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
                          v-for="newfield in currentFields(endpoint)" :key="newfield['label']"
                          @click="addField(newfield)">
                    {{ newfield["label"] }}
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
                <span v-if="show_loading" class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
              </button>
              <span v-if="show_loading" id="searching-focus" class="sr-only" tabindex="-1">Searching&nbsp;</span>
            </div>
            <div class="col-1"></div>
          </div>
        </div>
        <!--Docs links-->
        <div class="row">
          <div class="col-12">
            <p>
              Searching U.S. caselaw published through mid-2018. <a :href="urls.search_docs">Documentation</a>.<br>
              <strong>Need legal advice?</strong> This is not your best option! Read about
              <a :href="urls.search_docs + '#research'">our limitations and alternatives</a>.
            </p>
          </div>
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
        endpoint: "cases",
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
            /*
          {
            name: "court",
            value: "",
            label: "Court",
            choices: 'court',
            format: "e.g. ill-app-ct",
            info: ""
          },
          */
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
    beforeMount () {
      this.updateFields();
    },
    watch: {
      endpoint: {
        handler: function () {
          this.updateFields()
        }
      }
    },
    props: ['choices', 'search_error', 'field_errors', 'urls', 'show_loading'],
    methods: {
      updateFields() {
        this.fields = this.endpoints[this.endpoint].filter(endpoint => endpoint.default);
      },
      replaceFields(new_fields) {
        this.fields = new_fields;
      },
      removeField(field_to_remove) {
        for (let i = this.fields.length - 1; i >= 0; i--) {
          if (this.fields[i]['name'] === field_to_remove) {
            this.fields.splice(i, 1);
          }
        }
        this.$parent.updateUrlHash();
      },
      addField(field_to_add) {
        for (let i = this.fields.length - 1; i >= 0; i--) {
          if (this.fields[i]['name'] === field_to_add['name']) {
            return false;
          }
        }
        this.fields.push(field_to_add);
        this.$parent.updateUrlHash();
      },
      getFieldEntry(field_name, endpoint) {
        for (let i = this.endpoints[endpoint].length - 1; i >= 0; i--) {
          if (this.endpoints[endpoint][i]['name'] === field_name) {
            return this.endpoints[endpoint][i];
          }
        }
      },
      currentFields(endpoint) {
        let return_list = [];
        for (let field in this.endpoints[endpoint]) {
          if (!this.fields.includes(this.endpoints[endpoint][field])) {
            return_list.push(this.endpoints[endpoint][field])
          }
        }
        return return_list
      }
    }
  }
</script>
