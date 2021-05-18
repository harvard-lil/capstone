<template>
  <div class="search-form" id="sidebar-menu">
    <form @submit.prevent="$emit('new-search', $store.getters.fields, $store.getters.endpoint)"
          class="row">
      <div class="col-centered col-11">
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
              {{ $store.getters.endpoint }}
            </button>

            <div class="dropdown-menu" aria-labelledby="search-routes-dropdown">
              <a v-for="current_endpoint in Object.keys($parent.endpoints)" :key="current_endpoint"
                 @click="changeEndpoint(current_endpoint)"
                 :class="['dropdown-item', 'search-tab', current_endpoint===$store.getters.endpoint ? 'active' : '']">
                {{ current_endpoint }}
              </a>
            </div>
          </div>
        </div>

        <!-- Table showing search fields. Also includes add field and search buttons. -->
        <div v-if="$store.getters.search_error"
             role="alert"
             class="alert alert-danger">
          <p>{{ $store.getters.search_error }}</p>
          <h2 id="form-errors-heading" tabindex="-1" class="sr-only">
            {{ $store.getters.search_error }}
          </h2>
        </div>
        <div v-if="Object.keys($store.getters.field_errors).length"
             role="alert"
             class="alert alert-danger">
          <!--<p>Please correct the following <strong>2 error(s)</strong>: </p>-->
          <p>Please correct the following {{ Object.keys($store.getters.field_errors).length }} error(s):</p>
          <h2 id="form-errors-heading" tabindex="-1" class="sr-only">
            Please correct the following {{ Object.keys($store.getters.field_errors).length }} error(s)</h2>
          <ul class="bullets">
            <li v-for="(error, name) in $store.getters.field_errors"
                :key="'error' + name">
              <a :href="'#'+name">{{ getFieldByName(name).label }}:</a> {{ error }}
            </li>
          </ul>
        </div>

        <div class="search-fields row">
          <div v-for="field in $store.getters.fields"
               class="search-field"
               v-bind:class="{'default-field': field.default, 'shown': advanced_fields_shown && !field.default}"
               :key="field.name">
            <!--Fields default-->
            <template v-if="field.default">
              <field-item :field="field" :choices="$store.getters.choices[field.choices]"></field-item>
              <div v-if="field.default && $store.getters.field_errors[field.name]" class="invalid-feedback">
                {{ $store.getters.field_errors[field.name] }}
              </div>
              <small v-if="field.default && field.info"
                     :id="`help-text-${field.name}`"
                     class="form-text text-muted">
                {{ field.info }}
              </small>
            </template>
            <!--Other fields-->
            <template v-else>
              <template v-if="advanced_fields_shown">
                <field-item v-if="!field.default"
                            :field="field"
                            :choices="$store.getters.choices[field.choices]"
                            :key="field.name"></field-item>
                <div v-if="!field.default && $store.getters.field_errors[field.name]" class="invalid-feedback">
                  {{ $store.getters.field_errors[field.name] }}
                </div>
                <small v-if="!field.default && field.info"
                       :id="`help-text-${field.name}`"
                       class="form-text text-muted">
                  {{ field.info }}
                </small>
              </template>
            </template>
          </div>
        </div>
        <a href="#" class="btn btn-tertiary show-advanced-options"
           aria-label="Show or hide advanced filters"
           @click="advanced_fields_shown = !advanced_fields_shown">
          <span v-if="advanced_fields_shown">Hide advanced filters</span>
          <span v-else>Show advanced filters</span>
        </a>

        <!--Buttons row-->
        <div class="submit-button-group">
          <search-button :showLoading="$store.getters.showLoading" :endpoint="endpoint"></search-button>
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
              <query-explainer :query_url="$store.getters.query_url"></query-explainer>
            </div>
          </div>
        </div>
        <div class="search-disclaimer">
          <p>
            Searching U.S. caselaw published through mid-2018. <a :href="$store.getters.urls.search_docs">Documentation</a>.<br>
          </p>
          <p>
            <span class="bold">Need legal advice?</span> This is not your best option! Read about
            <a :href="$store.getters.urls.search_docs + '#research'">our limitations and alternatives</a>.
          </p>
        </div>
      </div>
    </form>
  </div>
</template>
<script>
import SearchButton from '../vue-shared/search-button';
import QueryExplainer from './query-explainer';
import FieldItem from './field-item';

export default {
  components: {
    FieldItem,
    SearchButton,
    QueryExplainer,
  },
  data: function () {
    return {
      query: [],
      show_explainer: false,
      advanced_fields_shown: false,
      defaultFields: [],
      otherFields: []
    }
  },
  methods: {
    getFieldByName(field_name) {
      return this.$parent.endpoints[this.endpoint].find(field => field.name === field_name);
    },
    changeEndpoint: function (new_endpoint) {
      this.$emit('update:endpoint', new_endpoint)
      this.$parent.updateQueryURL();
    },
    toggleExplainer() {
      this.show_explainer = !this.show_explainer;
    },
    downloadResults: function (format) {
      return this.$parent.assembleUrl() + "&format=" + format;
    },
  },
  mounted() {
    this.$parent.updateQueryURL();
  }
}
</script>
