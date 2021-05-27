<template>
  <div class="search-form" id="sidebar-menu" v-bind:class="{ 'results-shown': $store.getters.resultsShown }">
    <div class="row">
      <div class="col-centered col-11">
        <div class="col-md-2 empty-push-div"></div>
        <div class="col-md-10 title-container">
          <h3 class="page-title">
            Search
          </h3>
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
        <div v-if="$store.getters.erroredFieldList.length"
             role="alert"
             class="alert alert-danger">
          <p>Please correct the following {{ $store.getters.erroredFieldList.length }} error(s):</p>
          <h2 id="form-errors-heading" tabindex="-1" class="sr-only">
            Please correct the following
            <template v-if="$store.getters.erroredFieldList.length > 1">{{ $store.getters.erroredFieldList.length }} errors:</template>
            <template>error:</template>
          </h2>
          <ul class="bullets">
            <li v-for="field in $store.getters.erroredFieldList"
                :key="'error' + field">
              <a :href="'#'+field">{{ $store.getters.getField(field).label }}:</a> {{ $store.getters.getField(field).error }}
            </li>
          </ul>
        </div>

        <div class="search-fields row">
          <div class="search-field default-field">
            <field-item :field="$store.getters.getField('search')"></field-item>
            <div v-if="$store.getters.fieldHasError('search')" class="invalid-feedback">
              {{ $store.getters.getField('search').error }}
            </div>
            <small :id="`help-text-search`" class="form-text text-muted">
              {{ $store.getters.getField('search').info }}
            </small>
          </div>


          <template v-if="$store.getters.advanced_fields_shown">
            <div class="search-field shown">
              <field-item :field="$store.getters.getField('decision_date_min')"></field-item>
              <div v-if="$store.getters.fieldHasError('decision_date_min')" class="invalid-feedback">
                {{ $store.getters.getField('decision_date_min').error }}
              </div>
              <small :id="`help-text-decision_date_min`" class="form-text text-muted">
                {{ $store.getters.getField('decision_date_min').info }}
              </small>
            </div>

            <div class="search-field shown">
              <field-item :field="$store.getters.getField('decision_date_max')"></field-item>
              <div v-if="$store.getters.fieldHasError('decision_date_max')" class="invalid-feedback">
                {{ $store.getters.getField('decision_date_max').error }}
              </div>
              <small :id="`help-text-decision_date_max`" class="form-text text-muted">
                {{ $store.getters.getField('decision_date_max').info }}
              </small>
            </div>

            <div class="search-field shown">
              <field-item :field="$store.getters.getField('name_abbreviation')"></field-item>
              <div v-if="$store.getters.fieldHasError('name_abbreviation')" class="invalid-feedback">
                {{ $store.getters.getField('name_abbreviation').error }}
              </div>
              <small :id="`help-text-name_abbreviation`" class="form-text text-muted">
                {{ $store.getters.getField('name_abbreviation').info }}
              </small>
            </div>

            <div class="search-field shown">
              <field-item :field="$store.getters.getField('docket_number')"></field-item>
              <div v-if="$store.getters.fieldHasError('docket_number')" class="invalid-feedback">
                {{ $store.getters.getField('docket_number').error }}
              </div>
              <small :id="`help-text-docket_number`" class="form-text text-muted">
                {{ $store.getters.getField('docket_number').info }}
              </small>
            </div>

            <div class="search-field shown">
              <field-item :field="$store.getters.getField('reporter')"></field-item>
              <div v-if="$store.getters.fieldHasError('reporter')" class="invalid-feedback">
                {{ $store.getters.getField('reporter').error }}
              </div>
              <small :id="`help-text-reporter`" class="form-text text-muted">
                {{ $store.getters.getField('reporter').info }}
              </small>
            </div>

            <div class="search-field shown">
              <field-item :field="$store.getters.getField('jurisdiction')"></field-item>
              <div v-if="$store.getters.fieldHasError('jurisdiction')" class="invalid-feedback">
                {{ $store.getters.getField('jurisdiction').error }}
              </div>
              <small :id="`help-text-jurisdiction`" class="form-text text-muted">
                {{ $store.getters.getField('jurisdiction').info }}
              </small>
            </div>

            <div class="search-field shown">
              <field-item :field="$store.getters.getField('cite')"></field-item>
              <div v-if="$store.getters.fieldHasError('cite')" class="invalid-feedback">
                {{ $store.getters.getField('cite').error }}
              </div>
              <small :id="`help-text-cite`" class="form-text text-muted">
                {{ $store.getters.getField('cite').info }}
              </small>
            </div>

            <div class="search-field shown">
              <field-item :field="$store.getters.getField('court')"></field-item>
              <div v-if="$store.getters.fieldHasError('court')" class="invalid-feedback">
                {{ $store.getters.getField('court').error }}
              </div>
              <small :id="`help-text-court`" class="form-text text-muted">
                {{ $store.getters.getField('court').info }}
              </small>
            </div>
          </template>
        </div>
        <button class="btn btn-tertiary show-advanced-options"
           aria-label="Show or hide advanced filters"
           @click="$store.commit('toggleAdvanced')">
          <span v-if="$store.getters.advanced_fields_shown">Hide advanced filters</span>
          <span v-else>Show advanced filters</span>
        </button>

        <!--Buttons row-->
        <div class="submit-button-group">
          <div class="submit-btn-container">
            <button @click="$store.dispatch('searchFromForm')"
                    class="btn btn-primary d-flex align-items-center">
              Search
              <span v-if="$store.getters.showLoading"
                    class="spinner-border spinner-border-sm"
                    role="status"
                    aria-hidden="true"></span>
            </button>
            <span v-if="$store.getters.showLoading"
                  id="loading-focus"
                  class="sr-only"
                  tabindex="-1">Loading</span>
          </div>
          <button id="query-explainer-button" class="mt-0" @click="$store.commit('toggleExplainer')"
             v-if="$store.getters.show_explainer">HIDE API CALL
          </button>
          <button id="query-explainer-button" class="mt-0" @click="$store.commit('toggleExplainer')" v-else>SHOW API CALL</button>
        </div>
        <div class="query-explainer" v-show="$store.getters.show_explainer">
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
            Searching U.S. caselaw published through mid-2018. <a
              :href="$store.getters.urls.search_docs">Documentation</a>.<br>
          </p>
          <p>
            <span class="bold">Need legal advice?</span> This is not your best option! Read about
            <a :href="$store.getters.urls.search_docs + '#research'">our limitations and alternatives</a>.
          </p>
        </div>
      </div>
    </div>
  </div>
</template>
<script>
  import QueryExplainer from './query-explainer';
  import FieldItem from './field-item';

  export default {
    components: {
      QueryExplainer,
      FieldItem
    },
  }
</script>
