<template>
  <form v-on:submit.prevent>
    <div class="search-form-container col-centered">
      <searchroutes :endpoint="endpoint"></searchroutes>
      <br/>
      <!-- Table showing search fields. Also includes add field and search buttons. -->
      <div class="row">
        <template v-if="field_errors">
          <div v-for="(error, name) in field_errors"
               v-bind:key="'error' + name" class="col-12 alert alert-danger">
            <strong>
              <span v-text="getFieldEntry(name, endpoint).label + ':'"></span>
            </strong>&nbsp;
            <small>
              <span v-text="error"></span>
            </small>
          </div>
        </template>
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
              <template v-else-if="field['format']">
                <input v-model='field["value"]'
                       class="queryfield"
                       type="text"
                       :id='field["name"]'
                       :placeholder='field["format"]'>
              </template>
              <template v-else>
                <input v-model='field["value"]'
                       class="queryfield"
                       :id='field["name"]'
                       type="text">
              </template>
            </div>
            <div class="col-1">
              <div class="remfield">
                <button v-if="fields.length > 1"
                        class="field-button active"
                        @click="removeField(field['name'])">
                </button>
                <button v-if="fields.length <= 1"
                        class="field-button disabled"
                        disabled>
                </button>
              </div>

            </div>
          </div>
          <!--Add field row-->
          <div class="row">
            <div class="col-4"></div>
            <div class="col-7">
              <template v-if="fields.length > 0">
                <div class="dropdown addfield">
                  <button class="dropdown-toggle add-field-button btn-white-violet"
                          type="button"
                          id="dropdownMenuButton"
                          data-toggle="dropdown"
                          aria-haspopup="true"
                          aria-expanded="false">
                    Add Field
                  </button>
                  <div class="dropdown-menu" aria-labelledby="dropdownMenuButton">
                    <a class="dropdown-item" v-for="newfield in currentFields(endpoint)"
                       @click="addField(newfield)" v-bind:key="newfield['label']">
                      {{ newfield["label"] }}</a>
                  </div>
                </div>
              </template>

            </div>
            <div class="col-1"></div>
          </div>
          <!--Submit row-->
          <div class="row">
            <div class="col-4"></div>
            <div class="col-7">
              <input class="btn-default btn-submit"
                     @click="$emit('new-search', fields, endpoint)"
                     type="submit"
                     value="Search">
            </div>
            <div class="col-1"></div>
          </div>
        </div>

        For help using this tool, check out our <a :href="docs_url">Search Docs</a>.
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
        fields: [{
          name: "search",
          value: "",
          label: "Full-Text Search",
          default: true,
          format: "e.g. 'insurance' illinois",
          info: ""
        }],
        endpoints: {
          cases: [
            {
              name: "search",
              value: "",
              label: "Full-Text Search",
              default: true,
              format: "e.g. 'insurance' illinois",
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
              default: true,
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
    watch: {
      endpoint: {
        handler: function (newval) {
          this.updateFields(newval)
        }
      }
    },
    props: ['choices', 'field_errors', 'docs_url'],
    methods: {
      updateFields(new_endpoint) {
        this.fields = [];
        for (let i = this.endpoints[new_endpoint].length - 1; i >= 0; i--) {
          if (this.endpoints[new_endpoint][i]['default']) {
            this.fields.push(this.endpoints[new_endpoint][i]);
          }
        }
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
