<template>
  <div>
    <div class="page-title">
      <h1>Historical Trends</h1>
      <p>
        The <a href="/">Caselaw Access Project</a> collects 360 years of United States caselaw from the Harvard Law
        School Library — about 12 billion words in all. Our Historical Trends tool graphs the frequency
        of words and phrases through time, similar to the Google Ngram Viewer.
      </p>
    </div>
    <form @submit.prevent="submitForm">
      <div class="form-row query-row">
        <div class="col pr-0">
          <input class="text-to-graph"
                 v-model="textToGraph"
                 ref="textToGraph"
                 aria-label="terms to graph">
        </div>
        <loading-button :showLoading="showLoading" class="col-auto pl-0">Graph</loading-button>
        <div class="col-auto">
          <button class="btn-secondary "
                  type="button"
                  ref="helpButton"
                  data-toggle="collapse"
                  data-target="#helpPanel"
                  aria-expanded="false"
                  aria-controls="helpPanel">
            ADVANCED
          </button>
        </div>
      </div>
      <div class="collapse card"
           id="helpPanel"
           tabindex="-1"
           @keydown.esc="$refs.helpButton.click()">
        <div class="card-body">
          <button type="button"
                  class="close h40.7em"
                  data-toggle="collapse"
                  data-target="#helpPanel"
                  aria-controls="helpPanel"
                  aria-label="Close">
            <span aria-hidden="true">&times;</span>
          </button>

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
                      @click.prevent="appendJurisdictionCode(jurisdiction[0])"
              >{{jurisdiction[0]}}:</a>"
              </p>
            </div>
          </div>
        </div>
      </div>
      <div class="row">
        <div class="col-12 description small">
          Example searches:
          <example-link query="piracy"/> /
          <example-link query="he said, she said"/> /
          <example-link query="ride a *"/> /
          <example-link query="me: lobster, cal: gold, tex: cowboy"/> /
          <example-link query="*: gold"/> /
          <a href="#" @click.prevent="$refs.helpButton.click()">more ...</a>
        </div>
      </div>
    </form>

    <div class="row" v-if="errors.length">
      <ul class="small alert-danger">
        <li v-for="error in errors">{{error}}</li>  <!-- eslint-disable-line vue/require-v-for-key -->
      </ul>
    </div>

    <div v-if="chartData.datasets.length > 0" class="row graph-menu">
      <div class="col-auto ml-auto">
        <button class="btn-secondary"
                type="button"
                data-toggle="collapse"
                data-target="#optionsPanel"
                aria-expanded="false"
                aria-label="Customize graph display"
                title="Customize"
                aria-controls="optionsPanel">
          <img :src="`${urls.static}img/icons/settings.svg`">
        </button>
        <button class="btn-secondary"
                type="button"
                data-toggle="collapse"
                data-target="#citePanel"
                aria-expanded="false"
                aria-label="Cite graph"
                title="Cite"
                aria-controls="citePanel">
          <img :src="`${urls.static}img/icons/school.svg`">
        </button>
        <button class="btn-secondary"
                type="button"
                data-toggle="collapse"
                data-target="#downloadPanel"
                aria-expanded="false"
                aria-label="Download graph"
                title="Download"
                aria-controls="downloadPanel">
          <img :src="`${urls.static}img/icons/download.svg`">
        </button>
      </div>
    </div>

    <div id="collapsePanels">

      <!-- customize panel -->
      <div class="collapse card"
           id="optionsPanel"
           data-parent="#collapsePanels">
        <div class="card-body">
          <button type="button"
                  class="close h40.7em "
                  data-toggle="collapse"
                  data-target="#optionsPanel"
                  aria-controls="optionsPanel"
                  aria-label="Close"
          >
            <span aria-hidden="true">&times;</span>
          </button>
          <h5>Customize graph display</h5>
          <div class="form-group">
            <label for="min-year">Year range: from</label>
            <input id="min-year"
                   v-model.lazy.number="minYear"
                   type="number"
                   min="1640" max="2018"/>
            <label for="max-year"> To</label>
            <input id="max-year"
                   v-model.lazy.number="maxYear"
                   type="number"
                   min="1640" max="2018"/>
          </div>
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
        </div>
      </div>

      <!-- cite panel -->
      <div class="collapse card"
           id="citePanel"
           data-parent="#collapsePanels">
        <div class="card-body">
          <button type="button"
                  class="close h40.7em "
                  data-toggle="collapse"
                  data-target="#citePanel"
                  aria-controls="citePanel"
                  aria-label="Close">
            <span aria-hidden="true">&times;</span>
          </button>
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
        </div>
      </div>

      <!-- download panel -->
      <div class="collapse card"
           id="downloadPanel"
           data-parent="#collapsePanels">
        <div class="card-body">
          <button type="button"
                  class="close h40.7em "
                  data-toggle="collapse"
                  data-target="#downloadPanel"
                  aria-controls="downloadPanel"
                  aria-label="Close">
            <span aria-hidden="true">&times;</span>
          </button>
          <h5>Download</h5>
          <a href="#"
             download="image.png"
             @mousedown="setDownloadUrl"
             @touchstart="setDownloadUrl"
          >Download as an image</a>
        </div>
      </div>
    </div> <!-- /collapsePanels -->
    <div class="graph">
      <div class="container graph-container">
        <line-example :chartData="chartData"
                      :options="chartOptions"
                      :styles="chartStyles"
                      ref="chart"/>
      </div>
    </div>
  </div>
</template>

<script>
  import LineExample from './LineChart.vue';
  import LoadingButton from '../vue-shared/loading-button.vue';
  import debounce from 'lodash.debounce';
  import Chart from 'chart.js';
  import Vue from 'vue';

  export default {
    name: 'Main',
    components: {
      LineExample,
      LoadingButton,
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
      this.handleRouteUpdate(this.$route);
    },
    watch: {
      /* Read url state on change. */
      '$route': function (route, oldRoute) {
        this.handleRouteUpdate(route, oldRoute);
      },
      percentOrAbs: function (newval) {
        this.setNewQueries("percentOrAbs", newval);
      },
      countType: function (newval) {
        this.setNewQueries("countType", newval);
      },
      sameYAxis: function (newval) {
        this.setNewQueries("sameYAxis", newval);
      },
      minYear: function (newval) {
        this.setNewQueries("minYear", newval);
      },
      maxYear: function (newval) {
        this.setNewQueries("maxYear", newval);
      },
      smoothingFactor: function(newval) {
        this.setNewQueries("smoothingFactor", newval);
      }

    },
    data: function () {
      const chartHeight = 400;
      return {
        // citation stuff
        baseUrl: window.location.origin + this.$router.options.base,
        currentYear: new Date().getFullYear(),
        datasetVersion: "1.0",
        datasetDate: "June 6, 2019",
        datasetYear: "2019",
        author: "Harvard University",
        publication: "Caselaw Access Project Historical Trends",

        chartHeight: chartHeight,
        chartData: {datasets: []},
        chartNeedsRerender: false,
        rawData: null,
        textToGraph: "apple pie, baseball",
        minYear: 1800,
        maxYear: 2018,
        minPossible: 1640,
        maxPossible: 2018,
        smoothingFactor: 2,
        smoothingWindow: 0,
        countType: "doc_count",
        percentOrAbs: "percent",
        sameYAxis: true,
        previousSameYAxis: true,
        jurisdictions: [],
        jurisdictionLookup: {},
        urls: {},
        selectedJurs: [],
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
        chartOptions: {
          responsive: true,
          maintainAspectRatio: false,
          legend: {
            labels: {
              boxWidth: 20,
              usePointStyle: true,
            }
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
                const startRange = Math.max(data.labels[0], Number(label)-this.smoothingWindow);
                const endRange = Math.min(data.labels[data.labels.length-1], Number(label)+this.smoothingWindow);
                return `${startRange}-${endRange}`;
              },
              label: (tooltipItem, data) => {
                /*
                  format tooltip text based on percentOrAbs and countType,
                  like "term: X% of instances" or "term: Y cases"
                */
                let label = data.datasets[tooltipItem.datasetIndex].label + ': ';
                const value = tooltipItem.yLabel;
                const countType = this.countType === "count" ? "instances" : "cases";
                if (this.percentOrAbs === "percent") {
                  label += `${value.toPrecision(3)}% of ${countType}`;
                } else if (this.smoothingWindow) {
                  label += `about ${value < 10 ? value.toPrecision(2) : Math.round(value)} ${countType} per year`;
                } else {
                  label += `${tooltipItem.yLabel} ${countType}`;
                }
                return label;
              }
            }
          }
        },
        chartStyles: {
          height: `${chartHeight}px`,
        }
      }
    },
    computed: {
      currentUrl: function () {
        return this.baseUrl.slice(0, -1) + this.$route.fullPath;
      },
    },
    methods: {
      isValidYear(year) {
        return year === '' || (this.minPossible <= year && year <= this.maxPossible)
      },
      clampYears() {
        /* clamp minYear and maxYear to acceptable values */
        if (!this.isValidYear(this.minYear))
          this.minYear = this.minPossible;
        if (!this.isValidYear(this.maxYear))
          this.maxYear = this.maxPossible;
        if (this.maxYear && this.minYear && this.minYear > this.maxYear)
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
        /* copy the form state into the route to trigger a redraw */
        const query = {
          q: this.textToGraph,
          percentOrAbs: this.percentOrAbs,
          countType: this.countType,
          minYear: this.minYear,
          maxYear: this.maxYear,
          smoothingFactor: this.smoothingFactor
        };
        if (this.selectedJurs.length)
          query['jurs'] = this.selectedJurs;
        this.$router.push({
          path: '/',
          query
        });
      },
      handleRouteUpdate(route, oldRoute) {  // eslint-disable-line no-unused-vars
        // autofill form to match URL query
        const query = route.query;

        // update vals from query parameters
        if (query.q) {
          // only show loading icon if search text was changed
          this.showLoading = this.$route.query.q !== this.textToGraph;
          this.textToGraph = this.$route.query.q;
        }
        if (query.percentOrAbs)
          this.percentOrAbs = this.$route.query.percentOrAbs;
        if (query.countType)
          this.countType = this.$route.query.countType;
        if (query.sameYAxis)
          // sameYAxis expects a boolean
          this.sameYAxis = this.$route.query.sameYAxis === "true";
        if (query.minYear)
          this.minYear = Number(this.$route.query.minYear);
        if (query.maxYear)
          this.maxYear = Number(this.$route.query.maxYear);
        if (query.smoothingFactor)
          this.smoothingFactor = Number(this.$route.query.smoothingFactor);
        // clear existing errors, but don't clear existing graph yet in case we can't draw anything new
        this.errors = [];

        // validate input
        const q = query.q;
        if (q === undefined){
          // first load, with no query to run
          return;
        }
        if (!q.trim()){
          this.errors.push("Please enter text");
          return;
        }
        const terms = this.getTerms(q);

        Promise.all(

          // send request for each term, in parallel
          terms.map((term)=> {
            const [firstWord, ...restWords] = term.split(/\s/);

            // parse jurisdiction prefix
            let jursParams = "";
            if (firstWord.endsWith(':')) {
              const jur = firstWord.slice(0, -1);
              if (!this.jurisdictionLookup[jur]){
                this.errors.push(`Unknown jurisdiction "${jur}". Options are: ${Object.keys(this.jurisdictionLookup)}`);
                return null;
              }
              jursParams = "&jurisdiction=" + encodeURIComponent(jur);
              term = restWords.join(' ');
            }

            // fetch results
            const url = this.urls.api_root + "ngrams/?q=" + encodeURIComponent(term) + jursParams;
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
                return resp.results;
              })
          })
        ).then((results) => {
          // display results
          this.showLoading = false;
          const rawData = this.parseResponse(results);
          if (Object.keys(rawData.results).length === 0)
            return;  // no search term found results
          this.rawData = rawData;
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
        const minYear = Math.max(dataMinYear, this.minYear);
        const maxYear = Math.min(dataMaxYear, this.maxYear);
        let colorIndex = this.rawData.colorOffset;
        let fullChartReset = false;

        // prepare each dataset
        for (const [term, rawData] of Object.entries(this.rawData.results)) {

          // apply percentOrAbs and countType settings
          let data = rawData.map((year) => {
            if (year === null) return 0;
            if (this.percentOrAbs === "absolute") return year[this.countType][0];
            return year[this.countType][0]/year[this.countType][1]*100;
          });

          // apply minYear and maxYear settings
          data = data.slice(minYear-dataMinYear, maxYear-dataMinYear+1);

          // apply smoothingFactor setting
          data = this.movingAverage(data, maxYear-minYear);

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
          labels: this.range(minYear, maxYear+1),
          datasets: newDatasets,
        };

        // fullChartReset is a workaround for the yAxisID property not being reactive --
        // see https://github.com/apertureless/vue-chartjs/issues/177
        if (fullChartReset)
          this.$refs.chart.fullRerender(this.chartData, this.chartOptions);
      }, 200),
      parseResponse(apiResults) {
        const results = {};
        let minYear = null, maxYear = null;
        for (const result of apiResults) {
          if (result === null)
            continue;
          for (const [gram, jurs] of Object.entries(result)) {
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
              results[(jurName === "total" ? "" : this.jurisdictionLookup[jurName] + ": ") + gram] = years;
            }
          }
        }
        for (const key of Object.keys(results)){
          results[key] = results[key].slice(minYear, maxYear+1);
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
        return items.map((_, i) => this.average(items.slice(Math.max(i-window, 0), Math.min(i+window, items.length))));
      },
      average(items){
        return items.reduce((a, b) => a + b) / items.length
      },
      setNewQueries(newKey, newVal) {
        let oldQueries = this.$route.query;
        let newQueries = {};
        for (let key in oldQueries) {
          newQueries[key] = oldQueries[key];
        }
        newQueries[newKey] = newVal;
        this.$router.replace({
          path: '/',
          query: newQueries,
        });
      },
      appendJurisdictionCode(code) {
        if (this.textToGraph)
          this.textToGraph += ", ";
        this.textToGraph += code + ": ";
        this.$refs.textToGraph.focus();
      },
      setDownloadUrl(event) {
        /* when the Download url is clicked/right-clicked/touched, intercept the event and fill in the correct image data for download */
        const url=this.$refs.chart.$refs.canvas.toDataURL('image/png');
        const tag = event.currentTarget;
        tag.href=url;
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
    },
  }
</script>
