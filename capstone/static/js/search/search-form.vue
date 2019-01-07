<template>
    <form v-on:submit.prevent>
        <div class="row">
            <div class="col-12">
                <ul class="nav nav-tabs">
                    <li class="search-tab" v-for="(current_fields, current_endpoint) in endpoints">
                        <a v-if="current_endpoint == endpoint" @click="changeEndpoint(current_endpoint)"
                           class="nav-link active">{{ current_endpoint }}</a>
                        <a v-else @click="changeEndpoint(current_endpoint)"
                           class="nav-link">{{
                            current_endpoint }}</a>
                    </li>
                </ul>
            </div>
        </div>
        <div id="searchform">
            <div v-for="field in fields" v-bind:key="field['name']">
                <div class="row field_row_container">
                    <div class="col-4 field_label_container">
                        <label class="querylabel" :for="field['name']">{{ field["label"] }}</label><br>
                    </div>
                    <div class="col-7 field_value_container">
                        <template v-if="field['choices']">
                            <select v-model='field["value"]' :id='field["name"]'>
                                <option v-for="(label, value) in choiceLoader(field['choices'])" :value="value">{{ label
                                    }}
                                </option>
                            </select>
                        </template>
                        <template v-else-if="field['format']">
                            <input v-model='field["value"]' class="queryfield" :id='field["name"]' type="text"
                                   :placeholder='field["format"]'>
                        </template>
                        <template v-else>
                            <input v-model='field["value"]' class="queryfield" :id='field["name"]' type="text">\
                        </template>
                    </div>
                    <div class="col-1">
                        <div class="remfield">
                            <button v-if="fields.length > 1" class="field-button" @click="removeField(field['name'])">
                                &ndash;
                            </button>
                            <button v-if="fields.length <= 1" class="field-button disabled">&ndash;</button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        <div class="row field_row_container">
            <div class="col-4 field_label_container">
            </div>
            <div class="col-7 field_value_container">
                <template v-if="fields.length > 0">
                    <div class="dropdown addfield">
                        <button class="dropdown-toggle add-field-button btn-block" type="button" id="dropdownMenuButton"
                                data-toggle="dropdown" aria-haspopup="true" aria-expanded="false">Add Field
                        </button>
                        <div class="dropdown-menu" aria-labelledby="dropdownMenuButton">
                            <a class="dropdown-item" v-for="newfield in currentFields(endpoint)"
                               @click="addField(newfield)"
                               href="#">{{ newfield["label"] }}</a>
                        </div>
                    </div>
                </template>
            </div>
            <div class="col-1">
                <div class="remfield">
                </div>
            </div>
        </div>
        <div class="search-button-row row">
            <div class="col-11 text-right">
                <input @click="$emit('new-search', fields, endpoint)" type="submit" value="Search">
            </div>
        </div>
    </form>
</template>
<script>
    const endpoint_list = {
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
            info: "the case citation"
        },
        {
            name: "reporter",
            value: "",
            label: "Reporter",
            format: "e.g. ill-app-ct",
            info: ""
        },
        {
            name: "court",
            value: "",
            label: "Court",
            format: "e.g. ill-app-ct",
            info: ""
        },
        {
            name: "jurisdiction",
            value: "",
            label: "Jurisdiction",
            choices: 'jurisdiction',
            format: "e.g. ill-app-ct",
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
            label: "Long Name",
            format: "e.g. '1893'",
            info: "the year in which the reporter began publishing"
        },
        {
            name: "end_year",
            value: "",
            label: "Long Name",
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
};
    module.exports = {
            data: function () {
                return {
                    query: [],
                    newfield: null,
                    endpoint: 'cases',
                    fields: [endpoint_list['cases'][0]],
                    endpoints: endpoint_list
                }
            },
            beforeMount() {
                for (endpoint in endpoint_list) {
                    for (field in endpoint_list[endpoint]){
                            if ('choices' in endpoint_list[endpoint][field]) {
                                this.choiceLoader(endpoint_list[endpoint][field].choices);
                        }
                    }
                }
            },
            methods: {
                changeEndpoint: function (new_endpoint, new_fields=[]) {
                    this.$router.params.endpoint = new_endpoint
                    this.$parent.endpoint = new_endpoint // to update title
                    this.endpoint = new_endpoint;
                    this.fields = new_fields;
                    this.$emit('change-endpoint');
                    if (new_fields.length === 0 ) {
                        for (var i = this.endpoints[new_endpoint].length - 1; i >= 0; i--) {
                            if (this.endpoints[new_endpoint][i]['default']) {
                                this.fields.push(this.endpoints[new_endpoint][i]);
                            }
                        }
                    }
                },
                removeField: function (field_to_remove) {
                    for (var i = this.fields.length - 1; i >= 0; i--) {
                        if (this.fields[i]['name'] === field_to_remove) {
                            this.fields.splice(i, 1);
                        }
                    }
                },
                addField: function (field_to_add) {
                    for (var i = this.fields.length - 1; i >= 0; i--) {
                        if (this.fields[i]['name'] === field_to_add['name']) {
                            return false;
                        }
                    }
                    this.fields.push(field_to_add);
                },
                choiceLoader: function (choice) {
                    component = null;
                    if (app){
                        component = app;
                    } else if ('choices' in this.$parent) {
                        component = this.$parent;
                    }

                    if (choice in component.choices) {
                        return component.choices[choice];
                    }
                    if (choice == "whitelisted") {
                        return { "true": "Whitelisted", "false": "Not Whitelisted" }
                    }
                    component.startLoading();
                    return fetch(choice_source[choice])
                        .then(function (response) {
                            if (response.ok) {
                                return response.json();
                            }
                            if (response.status === 500) {
                                document.getElementById("loading-overlay").style.display = 'none';
                                //TODO Set up some kind of error condition
                            }
                        })
                        .then(function (results_json) {
                            component.choices[choice] = results_json;
                        })
                        .then(function () {
                            component.stopLoading();
                        })
                    },
                currentFields: function (endpoint) {
                    return_list = []
                    for (field in endpoint_list[endpoint]) {
                        if (!this.fields.includes(endpoint_list[endpoint][field])) {
                            return_list.push(endpoint_list[endpoint][field])
                        }
                    }
                    return return_list
                }
            }
    }
</script>
