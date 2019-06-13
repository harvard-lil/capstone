<template>
  <div>
    <div class="page-title">
      <h1>Historical Trends</h1>
      <p>
        The <a href="/">Caselaw Access Project</a> includes over 6 million U.S. legal cases from the Harvard Law
        School Library — about 12 billion words in all. Our Historical Trends tool graphs the frequency
        of words and phrases through time, similar to the Google Ngram Viewer.
      </p>
    </div>
    <form @submit.prevent="submitForm" class="d-flex flex-column">

      <!-- example links -- visually moved to end so dom order makes more sense for screen readers -->
      <div class="row order-3">
        <div class="col-12 description small">
          Example searches:
          <ul class="inline-list">
            <li><example-link query="piracy"/> <span aria-hidden="true"> / </span> </li>
            <li><example-link query="he said, she said"/> <span aria-hidden="true"> / </span> </li>
            <li><example-link query="ride a *"/> <span aria-hidden="true"> / </span> </li>
            <li><example-link query="me: lobster, cal: gold, tex: cowboy"/> <span aria-hidden="true"> / </span> </li>
            <li><example-link query="*: gold"/> <span aria-hidden="true"> / </span> </li>
            <li><a href="#" @click.prevent="clickHelpButton">more ...</a></li>
          </ul>
        </div>
      </div>

      <div class="form-row query-row">
        <div class="col pr-0">
          <input class="text-to-graph"
                 :value="textToGraph"
                 ref="textToGraph"
                 aria-label="terms to graph">
        </div>
        <loading-button :showLoading="showLoading" class="col-auto pl-0">Search</loading-button>
        <div class="col-auto">
          <panelset-button panel-id="help"
                           :current-panel="currentPanel"
                           title="Advanced search tips"
                           aria-label="advanced search tips">
            ADVANCED
          </panelset-button>
        </div>
      </div>
      <panelset-panel panel-id="help"
                      :current-panel="currentPanel">
        <div @click="helpLinkClicked">
          <h5>Search tips</h5>
          <p>
            Search for phrases of one to three words. Multiple phrases can be separated by commas. Do not use quotes.
            All searches are case-insensitive. Examples:
          </p>
          <ul class="bullets">
            <li><example-link query="piracy"/> (history of the term "piracy")</li>
            <li><example-link query="his or her"/> (history of the term "his or her")</li>
            <li><example-link query="apple, banana, orange, pear"/> (compare "apple" to "banana" to "orange" to "pear")</li>
            <li><example-link query="he said, she said"/> (compare "he said" to "she said")</li>
          </ul>

          <h5 class="card-title">Wildcard search</h5>
          <p>
            Replace the final word of a phrase with "*" to perform a wildcard search. This will return the top ten
            phrases beginning with your first one or two words. Wildcards are currently allowed only as the final
            word in a phrase. Examples:
          </p>
          <ul class="bullets">
            <li><example-link query="constitutional *"/> (top ten two-word phrases beginning with "constitutional")</li>
            <li><example-link query="ride a *"/> (top ten three-word phrases beginning with "ride a")</li>
            <li>* amendment (not currently supported)</li>
          </ul>

          <h5 class="card-title">Jurisdiction search</h5>
          <p>
            Limit a term to a particular jurisdiction (US state or state-level political division) by starting the term with
            that jurisdiction's code. Available jurisdiction codes are listed below. Examples:
          </p>
          <ul class="bullets">
            <li><example-link query="cal: gold mine"/> (history of the term "gold mine" in California)</li>
            <li><example-link query="me: lobster, cal: gold, tex: cowboy"/> (compare "lobster" in Maine, "gold" in California, and "cowboy" in Texas)</li>
          </ul>
          <p>
            Show all jurisdictions separately by using the special jurisdiction code "*". Examples:
          </p>
          <ul class="bullets">
            <li><example-link query="*: gold"/> (compare "gold" in all jurisdictions separately)</li>
          </ul>

          <h5 class="card-title">Jurisdiction codes</h5>
          <div class="row">
          <div class="col-4"
               v-for="jurisdiction in jurisdictions" :key="jurisdiction[0]">
            <p>
              {{jurisdiction[1]}}: "<a
                    :href="`?q=${jurisdiction[0]}}: `"
                    @click.prevent="appendJurisdictionCode(jurisdiction[0])">
              {{jurisdiction[0]}}:</a>"
            </p>
          </div>
        </div>
        </div>
      </panelset-panel>
    </form>

    <div class="row" v-if="errors.length">
      <ul class="small alert-danger">
        <li v-for="error in errors">{{error}}</li>  <!-- eslint-disable-line vue/require-v-for-key -->
      </ul>
    </div>

    <div v-if="chartData.datasets.length > 0" class="row graph-menu">
      <div class="col-auto ml-auto">
        <panelset-button panel-id="options" :current-panel="currentPanel" title="Customize">
          <img :src="`${urls.static}img/icons/settings.svg`">
          <span>Customize graph</span>
        </panelset-button>
        <panelset-button panel-id="table" :current-panel="currentPanel" title="Table view">
          <img :src="`${urls.static}img/icons/view_list.svg`">
          <span>Table view</span>
        </panelset-button>
        <panelset-button panel-id="cite" :current-panel="currentPanel" title="Cite">
          <img :src="`${urls.static}img/icons/school.svg`">
          <span>Cite graph</span>
        </panelset-button>
        <panelset-button panel-id="download" :current-panel="currentPanel" title="Download">
          <img :src="`${urls.static}img/icons/download.svg`">
          <span>Download</span>
        </panelset-button>
      </div>
    </div>

    <div id="collapsePanels">

      <!-- customize panel -->
      <panelset-panel panel-id="options" :current-panel="currentPanel">
        <h5>Customize graph display</h5>
        <fieldset class="form-group" aria-describedby="percentOrAbsHelpText">
          <p id="percentOrAbsHelpText" class="form-text">
            Show count as a percentage of all grams for the year, or an absolute number?
          </p>
          <div class="form-check form-check-inline">
            <input class="form-check-input"
                   type="radio"
                   name="percentOrAbs"
                   id="percentOrAbs1"
                   value="percent"
                   v-model="percentOrAbs">
            <label class="form-check-label" for="percentOrAbs1">Percentage</label>
          </div>
          <div class="form-check form-check-inline">
            <input class="form-check-input"
                   type="radio"
                   name="percentOrAbs"
                   id="percentOrAbs2"
                   value="absolute"
                   v-model="percentOrAbs">
            <label class="form-check-label" for="percentOrAbs2">Absolute number</label>
          </div>
        </fieldset>
        <fieldset class="form-group" aria-describedby="countTypeHelpText">
          <p id="countTypeHelpText" class="form-text">
            Show count of cases containing your term, or count of individual instances of your term?
          </p>
          <div class="form-check form-check-inline">
            <input class="form-check-input"
                   type="radio"
                   name="countType"
                   id="countType1"
                   value="doc_count"
                   v-model="countType">
            <label class="form-check-label" for="countType1">Case count</label>
          </div>
          <div class="form-check form-check-inline">
            <input class="form-check-input"
                   type="radio"
                   name="countType"
                   id="countType2"
                   value="count"
                   v-model="countType">
            <label class="form-check-label" for="countType2">Instance count</label>
          </div>
        </fieldset>
        <fieldset class="form-group" aria-describedby="sameYAxisHelpText">
          <p id="sameYAxisHelpText" class="form-text">
            Show all terms on the same Y axis (for comparing frequency) or scale each term to fill the Y axis (for
            comparing correlation)?
          </p>
          <div class="form-check form-check-inline">
            <input class="form-check-input"
                   type="radio"
                   name="sameYAxis"
                   id="sameYAxis1"
                   :value="true"
                   v-model="sameYAxis">
            <label class="form-check-label" for="sameYAxis1">Terms on the same Y axis</label>
          </div>
          <div class="form-check form-check-inline">
            <input class="form-check-input"
                   type="radio"
                   name="sameYAxis"
                   id="sameYAxis2"
                   :value="false"
                   v-model="sameYAxis">
            <label class="form-check-label" for="sameYAxis2">Terms scaled to fill Y axis</label>
          </div>
        </fieldset>
        <div class="form-group">
          <label for="formControlRange">Smoothing</label>
          <p id="smoothingFactorHelpText" class="form-text">
            <span v-if="smoothingFactor > 0">
              Data points will be averaged with the nearest {{smoothingFactor}}% of other points.
            </span>
            <span v-else>
              No smoothing will be applied.
            </span>
          </p>
          <input type="range"
                 class="form-control-range"
                 min="0" max="10"
                 v-model.lazy="smoothingFactor"
                 id="formControlRange">
        </div>
      </panelset-panel>

      <!-- table panel -->
      <panelset-panel panel-id="table" :current-panel="currentPanel">
        <h5>Table View</h5>
        <div class="table-responsive">
          <table class="table table-sm">
            <thead>
              <tr>
                <th scope="col">Year</th>
                <th v-for="dataset in chartData.datasets" scope="col">{{dataset.label}}</th> <!-- eslint-disable-line vue/require-v-for-key -->
              </tr>
            </thead>
            <tbody>
              <tr v-for="(year, i) in chartData.labels"> <!-- eslint-disable-line vue/require-v-for-key -->
                <th scope="row">{{year}}</th>
                <td v-for="dataset in chartData.datasets">{{formatValue(dataset.data[i])}}</td> <!-- eslint-disable-line vue/require-v-for-key -->
              </tr>
            </tbody>
          </table>
        </div>
      </panelset-panel>

      <!-- cite panel -->
      <panelset-panel panel-id="cite" :current-panel="currentPanel">
        <h5>Scholarly Citation and Reuse</h5>
        <p>
          Version: Historical Trends dataset version {{datasetVersion}}, published {{datasetDate}}.
        </p>
        <p>Graphs on this page may be freely reproduced with credit. Suggested citation formats:</p>
        <dl class="row">
          <dt class="col-sm-3">APA</dt>
          <dd class="col-sm-9">
            <!-- via https://columbiacollege-ca.libguides.com/apa/images -->
            "Graph of '{{textToGraph}},'"
            by {{author}}, {{datasetYear}}, {{publication}} v.{{datasetVersion}}.
            Retrieved [date], from {{currentUrl}}.
          </dd>
          <dt class="col-sm-3">MLA</dt>
          <dd class="col-sm-9">
            <!-- via image cited on the web only example from https://owl.purdue.edu/owl/research_and_citation/mla_style/mla_formatting_and_style_guide/mla_works_cited_electronic_sources.html -->
            <!-- title -->"Graph of '{{textToGraph}}.'"
            <!-- publication --><i>{{publication}} v.{{datasetVersion}}</i>,
            <!-- author -->{{author}}.
            <!-- publication date -->{{datasetDate}},
            <!-- url -->{{currentUrl}}.
            <!-- accessed date -->Accessed [date].
          </dd>
          <dt class="col-sm-3">Chicago / Turabian</dt>
          <dd class="col-sm-9">
            <!-- via http://www.easybib.com/guides/citation-guides/chicago-turabian/how-to-cite-a-photo-digital-image-chicago-turabian/ -->
            Graph of "{{textToGraph}}."
            {{datasetYear}}. {{publication}} v.{{datasetVersion}}, {{author}}, Cambridge, MA.
            {{currentUrl}}.
          </dd>
          <dt class="col-sm-3">Bluebook</dt>
          <dd class="col-sm-9">{{author}}, <i>{{publication}} v.{{datasetVersion}}</i>, Graph of "{{textToGraph}}," {{currentUrl}} (last visited [date]).</dd>
        </dl>
      </panelset-panel>

      <!-- download panel -->
      <panelset-panel panel-id="download" :current-panel="currentPanel">
        <h5>Download</h5>
        <ul class="bullets">
          <li><strong><a href="#" download="trends.png" @click="imageDownloadClicked" @contextmenu="imageDownloadClicked">Download as an image</a></strong></li>
          <li><a href="#" download="trends.csv" @click="csvDownloadClicked" @contextmenu="csvDownloadClicked">Download CSV</a> (best for analyzing in Excel)</li>
          <li><a href="#" download="trends.json" @click="jsonDownloadClicked" @contextmenu="jsonDownloadClicked">Download JSON</a> (best for analyzing from a program)</li>
        </ul>
        <p>
          View the API queries that generated this graph:
          <ul class="inline-list">
            <li v-for="(query, index) in currentApiQueries" v-bind:key="query">
              <a :href="query[1]" target="_blank">{{query[0]}}</a>
              <span v-if="index !== currentApiQueries.length - 1" aria-hidden="true"> / </span>
            </li>
          </ul>
        </p>
      </panelset-panel>
    </div> <!-- /collapsePanels -->
    <div class="sr-only sr-only-focusable graph-keyboard-instructions" tabindex="0">
      <strong>Keyboard controls:</strong> with the graph selected, use up and down arrows to select terms, left and right to select points,
      and enter key to enable or disable selected term.
    </div>
    <div class="graph">
      <div class="container graph-container"
           @keydown="chartKeyDown"
           tabindex="0">
        <line-example :chartData="chartData"
                      :options="chartOptions"
                      :styles="chartStyles"
                      :aria-label="`Graph of '${textToGraph}' between ${minYear} and ${maxYear}. See table view for details.`"
                      aria-describedby="tablePanelButton"
                      role="img"
                      ref="chart"/>
      </div>
      <div v-if="chartData.datasets.length > 0" class="row zoom-row">
        <div class="col-auto mr-2">years</div>
        <input id="min-year"
               class="col-auto"
               aria-label="start year"
               v-model.lazy.number="minYear"
               type="number"
               min="1640" max="2018"/>
        <vue-slider v-model="yearSlider"
                    class="col mr-3"
                    :enable-cross="false"
                    :min="minPossible"
                    :max="maxPossible"
        />
        <input id="max-year"
               class="col-auto"
               aria-label="end year"
               v-model.lazy.number="maxYear"
               type="number"
               min="1640" max="2018"/>
      </div>
    </div>
  </div>
</template>

<script>
  import LineExample from './LineChart.vue';
  import LoadingButton from '../vue-shared/loading-button.vue';
  import Panelset from '../vue-shared/panelset';
  import debounce from 'lodash.debounce';
  import Chart from 'chart.js';
  import Vue from 'vue';
  import VueSlider from 'vue-slider-component';
  import 'vue-slider-component/theme/default.css';
  import {encodeQueryData} from '../utils';
  import csvStringify from 'csv-stringify/lib/sync';

  // math helpers
  const mod = (n, m) => ((n % m) + m) % m;  // mod function that works correctly with negative numbers
  const max = Math.max;
  const min = Math.min;
  const average = (items) => items.reduce((a, b) => a + b) / items.length;
  const deepCopy = (value) => JSON.parse(JSON.stringify(value));

  export default {
    name: 'Main',
    mixins: [Panelset],
    components: {
      LineExample,
      LoadingButton,
      VueSlider,
      ExampleLink: Vue.component('example-link', {
        template: `<router-link class="example-link" :to="\`?q=\${query}\`">{{query}}</router-link>`,
        props: ['query'],
      }),
    },
    beforeMount() {
      this.jurisdictions = [["*", "Wildcard"]].concat(snippets.jurisdictions);  // eslint-disable-line
      for (const[k, v] of this.jurisdictions)
        this.jurisdictionLookup[k] = v;
      this.urls = urls;  // eslint-disable-line
      Chart.pluginService.register({
        beforeDraw: this.beforeDraw,
        afterLayout: this.afterLayout,
      });
    },
    mounted: function () {
      /* Read url state when first loaded. */
      const route = this.$route;
      this.initialQuery = deepCopy(route.query);
      this.handleRouteUpdate(route);
      // render default search manually if rendering won't be prompted by URL value
      if (!route.query.q)
        this.textToGraphUpdated();
    },
    watch: {
      /* Read url state on change. */
      '$route': function (route, oldRoute) {
        this.handleRouteUpdate(route, oldRoute);
      },
      textToGraph() {
        this.setUrlParam("textToGraph");
        this.textToGraphUpdated();
      },
      percentOrAbs: function () {
        this.setUrlParam("percentOrAbs");
        this.graphResults();
      },
      countType: function () {
        this.setUrlParam("countType");
        this.graphResults();
      },
      sameYAxis: function () {
        this.setUrlParam("sameYAxis");
        this.graphResults();
      },
      minYear: function () {
        this.clampYears();
        this.yearSlider = [this.minYear, this.maxYear];
        this.setUrlParam("minYear");
        this.graphResults();
      },
      maxYear: function () {
        this.clampYears();
        this.yearSlider = [this.minYear, this.maxYear];
        this.setUrlParam("maxYear");
        this.graphResults();
      },
      yearSlider(newval) {
        [this.minYear, this.maxYear] = newval;
      },
      smoothingFactor: function() {
        this.setUrlParam("smoothingFactor");
        this.graphResults();
      },
      deselectedTerms: function() {
        this.setUrlParam("deselectedTerms");
        this.graphResults();
      },
      currentLine() {
        this.selectLine();
      },
      currentPoint() {
        this.selectPoint();
      },
    },
    data: function () {
      const chartHeight = 400;
      // configure all the data values that have their state stored in the URL
      const urlValues = {
        textToGraph: {param: "q", default: "apple pie, baseball"},
        smoothingFactor: {param: "sf", default: 2},
        maxYear: {
          param: "xy",
          default: 2018,
          toValue: this.clampYear,
          isDefault: (value) => this.rawData && value === this.rawData.maxYear,
        },
        minYear: {
          param: "ny",
          default: 1800,
          toValue: this.clampYear,
          isDefault: (value) => this.rawData && value === this.rawData.minYear,
        },
        sameYAxis: {param: "sy", default: true},
        countType: {param: "ct", default: "doc_count"},
        percentOrAbs: {param: "pa", default: "percent"},
        deselectedTerms: {
          param: "dt",
          default: [],
          toValue: (value) => value.split(","),
          toParam: (value) => value.join(","),
        },
      };
      const out = {
        // citation stuff
        baseUrl: window.location.origin + this.$router.options.base,
        currentYear: new Date().getFullYear(),
        datasetVersion: "1.0",
        datasetDate: "June 6, 2019",
        datasetYear: "2019",
        author: "Harvard University",
        publication: "Caselaw Access Project Historical Trends",

        urlValues,
        yearSlider: [urlValues.minYear.default, urlValues.maxYear.default],

        currentTab: null,
        currentLine: null,
        currentPoint: null,
        currentHelpPanel: null,
        currentApiQueries: [],
        chartHeight: chartHeight,
        chartData: {datasets: []},
        chartNeedsRerender: false,
        rawData: null,
        textToGraph: "apple pie, baseball",
        minPossible: urlValues.minYear.default,
        maxPossible: urlValues.maxYear.default,
        smoothingWindow: 0,
        previousSameYAxis: true,
        jurisdictions: [],
        jurisdictionLookup: {},
        urls: {},
        // colors via http://mkweb.bcgsc.ca/biovis2012/ and https://contrast-ratio.com/:
        // these colors work for color-blindness, and have contrast against white that is WCAG AA large or better
        colors: [
          "rgb(0,0,0)", "rgb(73,0,146)", "rgb(146,0,0)",
          "rgb(0,73,73)", "rgb(0,109,219)", "rgb(146,73,0)",
          "rgb(0,146,146)", "rgb(182,109,255)", "rgb(219,109,0)",
        ],
        pointStyles: ['circle', 'cross', 'crossRot', 'rect', 'rectRounded', 'rectRot', 'star', 'triangle'],
        errors: [],
        showLoading: false,
        initialQuery: null,
        chartOptions: {
          responsive: true,
          maintainAspectRatio: false,
          // onClick: this.chartOnClick,
          legend: {
            labels: {
              boxWidth: 20,
              usePointStyle: true,
            },
            onClick: this.legendItemOnClick,
          },
          layout: {
            padding: {
              bottom: 10,
            }
          },
          scales: {
            yAxes: [{
              id: '0',
              type: 'linear',
              gridLines: {
                color: "rgba(0, 0, 0, 0)",
              },
              ticks: {
                beginAtZero: true,
              }
            }],
            xAxes: [{
              gridLines: {
                color: "rgba(0, 0, 0, 0)",
              },
            }]
          },
          tooltips: {
            callbacks: {
              title: (tooltipItem, data) => {
                /* format tooltip title to include date range when smoothing is on */
                const label = tooltipItem[0].label;
                if (!this.smoothingWindow)
                  return label;
                const startRange = max(data.labels[0], Number(label)-this.smoothingWindow);
                const endRange = min(data.labels[data.labels.length-1], Number(label)+this.smoothingWindow);
                return `${startRange}-${endRange}`;
              },
              label: (tooltipItem, data) => {
                return data.datasets[tooltipItem.datasetIndex].label + ': ' + this.formatValue(tooltipItem.yLabel);
              }
            }
          }
        },
        chartStyles: {
          height: `${chartHeight}px`,
        }
      };
      // add each urlValues entry to data
      for (const [k, v] of Object.entries(urlValues))
        out[k] = deepCopy(v['default']);
      return out;
    },
    computed: {
      currentUrl: function () {
        return this.baseUrl.slice(0, -1) + this.$route.fullPath;
      },
    },
    methods: {
      formatValue(value) {
        /*
          format numeric datapoint based on percentOrAbs, countType, and smoothingWindow
        */
        const countType = this.countType === "count" ? "instances" : "cases";
        if (this.percentOrAbs === "percent") {
          return `${!value ? 0 : value === 100 ? 100 : value.toPrecision(2)}% of ${countType}`;
        } else if (this.smoothingWindow) {
          return `about ${value < 10 ? value.toPrecision(2) : Math.round(value)} ${countType} per year`;
        } else {
          return `${value} ${countType}`;
        }
      },
      clampYear(year) {
        return max(min(Number(year), this.maxPossible), this.minPossible);
      },
      clampYears() {
        /* clamp minYear and maxYear to acceptable values */
        this.minYear = this.clampYear(this.minYear);
        this.maxYear = this.clampYear(this.maxYear);
        if (this.minYear > this.maxYear)
          [this.minYear, this.maxYear] = [this.maxYear, this.minYear];
      },
      range(start, stop, step = 1) {
        start = Number(start);
        stop = Number(stop);
        return Array(Math.ceil((stop - start) / step)).fill(start).map((x, y) => x + y * step)
      },
      getTerms(text) {
        let terms = text.split(",");
        return terms.map(term => term.trim());
      },
      submitForm() {
        this.textToGraph = this.$refs.textToGraph.value;
      },
      handleRouteUpdate(route) {
        /* set data values based on query params */
        const query = route.query;
        for (const [attr, config] of Object.entries(this.urlValues)) {
          let value = query[config.param];
          if (value) {
            if (config.toValue)
              value = config.toValue(value);
            this[attr] = value;
          }
        }
      },
      setUrlParam(attr) {
        /* set query params based on data value */
        const config = this.urlValues[attr];
        let value = this[attr];
        const query = deepCopy(this.$route.query);
        const toParam = config.toParam || ((v) => v);
        const isDefault = config.isDefault ? config.isDefault(value) : toParam(config.default) === toParam(value);
        if (isDefault)
          delete query[config.param];
        else
          query[config.param] = toParam(value);
        this.$router.replace({query});
      },
      getApiUrl(endpoint, params) {
        return `${this.urls.api_root}${endpoint}/?${encodeQueryData(params)}`;
      },
      textToGraphUpdated() {
        /* handle update to this.textToGraph */

        // clear existing errors, but don't clear existing graph yet in case we can't draw anything new
        this.errors = [];

        // validate input
        let q = this.textToGraph;
        if (!q.trim()){
          this.errors.push("Please enter text");
          return;
        }
        const terms = this.getTerms(q);
        this.showLoading = true;
        this.currentApiQueries = [];

        Promise.all(

          // send request for each term, in parallel
          terms.map((term)=> {
            if (term === "")
              return null;
            const [firstWord, ...restWords] = term.split(/\s/);

            // parse jurisdiction prefix
            const params = {};
            if (firstWord.endsWith(':')) {
              const jur = firstWord.slice(0, -1);
              if (!this.jurisdictionLookup[jur]){
                this.errors.push(`Unknown jurisdiction "${jur}". Options are: ${Object.keys(this.jurisdictionLookup)}`);
                return null;
              }
              if (!restWords.length) {
                this.errors.push(`Jurisdiction ${jur} should be followed by a search term.`);
                return null;
              }
              params.jurisdiction = jur;
              params.q = restWords.join(' ');
            } else {
              params.q = term;
            }

            // fetch results
            const url = this.getApiUrl("ngrams", params);
            this.currentApiQueries.push([term, url]);
            return fetch(url)

              // json parse each response
              .then((resp) => {
                if (!resp.ok)
                  throw resp;
                return resp.json();

              // filter out responses with no results
              }).then((resp)=>{
                if (Object.keys(resp.results).length === 0) {
                  this.errors.push(`"${term}" appears fewer than 100 times in our corpus.`);
                  return null;
                }
                return {results: resp.results, params};
              })
          })
        ).then((results) => {
          // display results
          this.showLoading = false;
          const rawData = this.parseResponse(results);
          if (Object.keys(rawData.results).length === 0)
            return;  // no search term found results
          this.rawData = rawData;

          // reset (some) graph settings when a new search is run.
          // we *don't* reset graph settings if this is the first query, and they were set in the URL,
          // because we want to preserve settings in shared links
          if (!this.initialQuery || !this.initialQuery[this.urlValues.minYear.param])
            this.minYear = this.rawData.minYear;
          if (!this.initialQuery || !this.initialQuery[this.urlValues.maxYear.param])
            this.maxYear = this.rawData.maxYear;
          if (!this.initialQuery || !this.initialQuery[this.urlValues.deselectedTerms.param])
            this.deselectedTerms = [];
          this.initialQuery = null;

          this.graphResults();
        }).catch(response => {
          // error handling
          this.showLoading = false;
          this.errors.push("Connection error: failed to load results");
          console.log("Connection error:", response);  // eslint-disable-line
        });

      },
      // graphResults is debounced so we don't redraw the graph too often when settings are changed
      graphResults: debounce(function(){

        // validate input from display options
        this.clampYears();
        if (!this.rawData)
          return;
        const newDatasets = [];
        const dataMinYear = this.rawData.minYear;
        const dataMaxYear = this.rawData.maxYear;
        const minYear = this.minYear;
        const maxYear = this.maxYear;
        let colorIndex = this.rawData.colorOffset;
        let fullChartReset = false;
        const years = this.range(minYear, maxYear+1);

        // prepare each dataset
        for (const [term, rawData] of Object.entries(this.rawData.results)) {

          // apply percentOrAbs and countType settings
          let data = rawData.data.map((year) => {
            if (year === null) return 0;
            if (this.percentOrAbs === "absolute") return year[this.countType][0];
            return year[this.countType][0]/year[this.countType][1]*100;
          });

          // apply smoothingFactor setting
          data = this.movingAverage(data, dataMaxYear-dataMinYear);

          // apply minYear and maxYear settings
          // the zero arrays and min/max functions handle the case where we are zoomed out or in from the actual data
          data = Array(max(dataMinYear-minYear, 0)).fill(0).concat(
            data.slice(max(minYear-dataMinYear, 0), min(maxYear-dataMinYear+1, data.length)),
            Array(max(maxYear-dataMaxYear, 0)).fill(0),
          );

          // rotate colors
          const color = this.colors[colorIndex++ % this.colors.length];

          // show individual points if we have fewer than 50 total
          const pointRadius = maxYear-minYear < 50 ? 3 : 0;

          newDatasets.push({
            label: term,
            borderColor: color,
            backgroundColor: "rgba(0, 0, 0, 0)",
            borderWidth: 2,
            borderRadius: 100,
            data: data,
            pointStyle: this.pointStyles[colorIndex % this.pointStyles.length],
            pointRadius: pointRadius,
            pointHitRadius: 5,
            yAxisID: this.sameYAxis ? '0' : newDatasets.length.toString(),
            hidden: this.deselectedTerms.includes(term),
          });
        }

        // handle this.sameYAxis
        const yAxes = this.chartOptions.scales.yAxes;
        if (!this.sameYAxis) {
          yAxes[0].display = false;
          if (yAxes.length < newDatasets.length) {
            fullChartReset = true;
            for (let i=yAxes.length;i<newDatasets.length;i++) {
              yAxes.push(Object.assign({}, yAxes[0], {'id': i.toString()}));
            }
          }
        } else {
          yAxes[0].display = true;
        }
        if (this.sameYAxis !== this.previousSameYAxis) {
          this.previousSameYAxis = this.sameYAxis;
          fullChartReset = true;
        }

        // show chart
        this.chartData = {
          labels: years,
          datasets: newDatasets,
        };

        // fullChartReset is a workaround for the yAxisID property not being reactive --
        // see https://github.com/apertureless/vue-chartjs/issues/177
        if (fullChartReset)
          this.$refs.chart.renderChart(this.chartData, this.chartOptions);
      }, 50),
      parseResponse(apiResults) {
        const results = {};
        let minYear = null, maxYear = null;
        for (const result of apiResults) {
          if (result === null)
            continue;
          for (const [gram, jurs] of Object.entries(result.results)) {
            for (const [jurName, jurData] of Object.entries(jurs)) {
              const years = new Array(this.maxPossible + 1).fill(null);
              for (const yearData of jurData) {
                let year = yearData['year'];
                if (year === "total")
                  continue;
                year = parseInt(year, 10);
                if (minYear === null || minYear > year)
                  minYear = year;
                if (maxYear === null || maxYear < year)
                  maxYear = year;
                years[year] = yearData;
              }
              results[(jurName === "total" ? "" : this.jurisdictionLookup[jurName] + ": ") + gram] = {
                data: years,
                params: result.params,
              };
            }
          }
        }
        minYear = max(minYear, this.minPossible);
        maxYear = min(maxYear, this.maxPossible);
        for (const key of Object.keys(results)){
          results[key].data = results[key].data.slice(minYear, maxYear+1);
        }
        // set a random colorOffset for this response, so colors change on each request
        const colorOffset = Math.floor(Math.random() * this.colors.length);
        return {colorOffset, minYear, maxYear, results};
      },
      movingAverage(items, totalRange) {
        /* average each item in items along with smoothingFactor % of adjacent items */
        const window = Math.floor(totalRange * (this.smoothingFactor/100));
        this.smoothingWindow = window;
        if (window < 1)
          return items;
        return items.map((_, i) => average(items.slice(max(i-window, 0), min(i+window, items.length))));
      },
      appendJurisdictionCode(code) {
        if (this.textToGraph)
          this.textToGraph += ", ";
        this.textToGraph += code + ": ";
        this.$refs.textToGraph.focus();
      },
      imageDownloadClicked(event) {
        /* when the Download url is clicked/right-clicked/touched, intercept the event and fill in the correct data for download */
        const payload = this.$refs.chart.$refs.canvas.toDataURL('image/png');
        event.currentTarget.href = payload;
      },
      jsonDownloadClicked(event) {
        /* when the Download url is clicked/right-clicked/touched, intercept the event and fill in the correct data for download */
        let payload = deepCopy(this.rawData);
        delete payload.colorOffset;
        payload = "data:application/json;base64," + btoa(JSON.stringify(payload, null, 2));
        event.currentTarget.href = payload;
      },
      csvDownloadClicked(event) {
        /* when the Download url is clicked/right-clicked/touched, intercept the event and fill in the correct data for download */
        const results = this.rawData.results;
        const terms = Object.keys(results);
        let payload = [];
        payload.push(["", ...terms.flatMap((term)=>[term, "", "", ""])]);
        payload.push(["", ...terms.flatMap(()=>["case count", "case denominator", "instance count", "instance denominator"])]);
        for (const [i, year] of this.chartData.labels.entries()) {
          payload.push([year, ...terms.flatMap((key)=>{
            const data = results[key].data[i];
            if (data === null)
              return ["", "", "", ""];
            else
              return [data.doc_count[0], data.doc_count[1], data.count[0], data.count[1]];
          })]);
        }
        payload = "data:text/csv;base64," + btoa(csvStringify(payload));
        event.currentTarget.href = payload;
      },
      chartKeyDown(event) {
        /* handle keyboard events on chart */
        switch (event.key) {
          case "ArrowDown":
            this.currentLine = mod(this.currentLine === null ? 0 : this.currentLine + 1, this.chartData.datasets.length);
            break;
          case "ArrowUp":
            this.currentLine = mod(this.currentLine === null ? 0 : this.currentLine - 1, this.chartData.datasets.length);
            break;
          case "ArrowRight":
            this.currentPoint = mod(this.currentPoint === null ? 0 : this.currentPoint + 1, this.chartData.labels.length);
            break;
          case "ArrowLeft":
            this.currentPoint = mod(this.currentPoint === null ? 0 : this.currentPoint - 1, this.chartData.labels.length);
            break;
          case "Enter":
            if (this.currentLine !== null)
              this.clickLegendItem(this.currentLine);
            break;
          default:
            return;
        }
        event.preventDefault();
      },
      selectLine() {
        /* handle update to this.currentLine */
        const datasets = this.chartData.datasets;
        const index = this.currentLine;
        for (const [i, dataset] of datasets.entries()) {
          if (index === i) {
            dataset.borderWidth = 4;
          } else {
            dataset.borderWidth = 2;
          }
        }
        this.chartOptions.animation = {duration: 0};
        this.$refs.chart.renderChart(this.chartData, this.chartOptions);
        delete this.chartOptions.animation;
        if (this.currentPoint !== null)
          this.selectPoint();
      },
      selectPoint() {
        /* handle update to this.currentPoint */
        if (this.currentLine === null)
          this.currentLine = 0;
        const chart = this.$refs.chart.$data._chart;
        const meta = chart.getDatasetMeta(this.currentLine);
        const rect = chart.canvas.getBoundingClientRect();
        const point = meta.data[this.currentPoint].getCenterPoint();
        chart.canvas.dispatchEvent(new MouseEvent('mousemove', {
          clientX: rect.left + point.x,
          clientY: rect.top + point.y
        }));
      },
      clickLegendItem(datasetIndex) {
        /* trigger a click event on legend item for given dataset index */
        const chart = this.$refs.chart.$data._chart;
        const legend = chart.legend;
        legend.options.onClick.call(legend, null, legend.legendItems[datasetIndex]);
      },
      legendItemOnClick(e, legendItem) {
        /* handle click on legend item */
        const term = this.chartData.datasets[legendItem.datasetIndex].label;
        const index = this.deselectedTerms.indexOf(term);
        if (index === -1)
          this.deselectedTerms.push(term);
        else
          this.deselectedTerms.splice(index, 1);
      },
      chartOnClick(e, targets) {
        if (!targets.length)
          return;
        const chart = this.$refs.chart.$data._chart;
        const point = chart.getElementAtEvent(e)[0];
        const year = this.chartData.labels[point._index];
        const term = this.chartData.datasets[point._datasetIndex].label;
        const params = this.rawData.results[term].params;
        const searchParams = {
          search: `"${params.q}"`,
          decision_date_min: `${year}-01-01`,
          decision_date_max: `${year}-12-31`,
        };
        if (params.jurisdiction)
          searchParams.jurisdiction = params.jurisdiction;
        const url = `${this.urls.search_page}?${encodeQueryData(searchParams)}`;
        window.open(url, '_blank');
      },
      beforeDraw(chart) {
        /* draw the chart background (white background and credit line) */
        const ctx = chart.chart.ctx;
        const canvas = ctx.canvas;
        const w = canvas.clientWidth;
        const h = canvas.clientHeight;
        ctx.save();
        // white background for PNG download
        ctx.fillStyle = "#FFF";
        ctx.fillRect(0, 0, w, h);
        // credit text
        ctx.fillStyle = "#888";
        ctx.font = "10px Arial";
        ctx.textAlign = "right";
        ctx.fillText(`Caselaw Access Project${w>400?' at Harvard Law School':''}. ${this.baseUrl}`, w-5, h-11);
        ctx.restore();
      },
      afterLayout(chart) {
        /* make room for the legend, once we know how big it will be, by resizing the chart */
        const newHeight = `${this.chartHeight-32+chart.legend.height}px`;
        if (newHeight !== this.chartStyles.height)
          this.chartStyles.height = newHeight;
      },
      clickHelpButton() {
        document.getElementById('helpPanelButton').click();
      },
      helpLinkClicked(event) {
        /* hide the help panel when a link inside is clicked */
        if (event.target.tagName === "A")
          this.clickHelpButton();
      }
    },
  }
</script>
