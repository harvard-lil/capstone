<template>
  <div>
    <div class="page-title">
      <h1>Ngrams</h1>
      <p>View words and phrases in U.S. case law through time.</p>
    </div>
    <form @submit.prevent="submitForm">
      <div class="form-group">
        <div class="row">
          <input class="col-lg-12 text-to-graph"
                 v-model="textToGraph">
          <div class="col-lg-12 description small">
            Example searches:
            <a class="example-link" href="#/?q=apple, banana, orange">
              apple, banana, orange
            </a>
            /
            <a class="example-link" href="#/?q=he said, she said">
              he said, she said
            </a>
            /
            <a class="example-link" href="#/?q=a dangerous *">
              a dangerous *
            </a>
            /
            <a class="example-link" href="#/?q=me: lobster, cal: gold, tex: cowboy">
              me: lobster, cal: gold, tex: cowboy
            </a>
            /
            <a class="example-link" href="#/?q=*: apples">
              *: apples
            </a>
          </div>
        </div>
        <div class="row">
          <div class="ml-auto mr-3">
            <button class="btn-secondary"
                    type="button"
                    data-toggle="collapse"
                    data-target="#optionsPanel"
                    aria-expanded="false"
                    aria-controls="optionsPanel">
              Graph options
            </button>
          </div>
          <div class="mr-3">
            <button class="btn-secondary"
                    type="button"
                    data-toggle="collapse"
                    data-target="#helpPanel"
                    aria-expanded="false"
                    aria-controls="optionsPanel">
              Help
            </button>
          </div>
          <div class="">
            <loading-button :showLoading="showLoading">Graph</loading-button>
          </div>
        </div>
        <div class="row" v-if="errors.length">
          <ul class="small alert-danger">
            <li v-for="error in errors">{{error}}</li>  <!-- eslint-disable-line vue/require-v-for-key -->
          </ul>
        </div>
      </div><!-- end form -->
    </form>
    <div class="collapse" id="helpPanel">
      <div class="card card-body">
        <h5 class="card-title">Wildcard search</h5>
        <p>
          Search for all terms ending with a word by adding a "*" to the end, like
          "<a href="#/?q=ride a *">ride a *</a>".
        </p>
        <h5 class="card-title">Jurisdiction search</h5>
        <p>
          Limit a term to a particular jurisdiction by starting the term with that jurisdiction's code and a colon,
          like "<a href="#/?q=cal: gold mine">cal: gold mine</a>".
        </p>
        <p>
          Show all jurisdictions separately with a *, like "<a href="#/?q=*: apples">*: apples</a>".
        </p>
        <h5 class="card-title">Jurisdiction codes</h5>
        <div class="row">
          <div class="col-4"
               v-for="jurisdiction in jurisdictions" :key="jurisdiction[0]">
            <p>{{jurisdiction[1]}}: "{{jurisdiction[0]}}:"</p>
          </div>
        </div>
      </div>
    </div>
    <div class="collapse" id="optionsPanel">
      <div class="card card-body">
        <div class="form-group">
          <label for="min-year">From</label>
          <input id="min-year"
                 @change="graphResults"
                 v-model.number="minYear"
                 type="number"
                 min="1640" max="2018"/>
          <label for="max-year"> To</label>
          <input id="max-year"
                 @change="graphResults"
                 v-model.number="maxYear"
                 type="number"
                 min="1640" max="2018"/>
        </div>
        <fieldset class="form-group" aria-describedby="percentOrAbsHelpText">
          <small id="percentOrAbsHelpText" class="form-text text-muted">
            Show count as a percentage of all grams for the year, or an absolute number?
          </small>
          <div class="form-check form-check-inline">
            <input class="form-check-input"
                   type="radio"
                   name="percentOrAbs"
                   id="percentOrAbs1"
                   value="percent"
                   @change="graphResults"
                   v-model="percentOrAbs">
            <label class="form-check-label" for="percentOrAbs1">Percentage</label>
          </div>
          <div class="form-check form-check-inline">
            <input class="form-check-input"
                   type="radio"
                   name="percentOrAbs"
                   id="percentOrAbs2"
                   value="absolute"
                   @change="graphResults"
                   v-model="percentOrAbs">
            <label class="form-check-label" for="percentOrAbs2">Absolute number</label>
          </div>
        </fieldset>
        <fieldset class="form-group" aria-describedby="countTypeHelpText">
          <small id="countTypeHelpText" class="form-text text-muted">
            Show count of cases containing your term, or count of individual instances of your term?
          </small>
          <div class="form-check form-check-inline">
            <input class="form-check-input"
                   type="radio"
                   name="countType"
                   id="countType1"
                   value="doc_count"
                   @change="graphResults"
                   v-model="countType">
            <label class="form-check-label" for="countType1">Case count</label>
          </div>
          <div class="form-check form-check-inline">
            <input class="form-check-input"
                   type="radio"
                   name="countType"
                   id="countType2"
                   value="count"
                   @change="graphResults"
                   v-model="countType">
            <label class="form-check-label" for="countType2">Instance count</label>
          </div>
        </fieldset>
        <fieldset class="form-group" aria-describedby="sameYAxisHelpText">
          <small id="sameYAxisHelpText" class="form-text text-muted">
            Show all terms on the same Y axis (for comparing frequency) or scale each term to fill the Y axis (for comparing correlation)?
          </small>
          <div class="form-check form-check-inline">
            <input class="form-check-input"
                   type="radio"
                   name="sameYAxis"
                   id="sameYAxis1"
                   :value="true"
                   @change="graphResults"
                   v-model="sameYAxis">
            <label class="form-check-label" for="sameYAxis1">Terms on the same Y axis</label>
          </div>
          <div class="form-check form-check-inline">
            <input class="form-check-input"
                   type="radio"
                   name="sameYAxis"
                   id="sameYAxis2"
                   :value="false"
                   @change="graphResults"
                   v-model="sameYAxis">
            <label class="form-check-label" for="sameYAxis2">Terms scaled to fill Y axis</label>
          </div>
        </fieldset>
        <div class="form-group">
          <label for="formControlRange">Smoothing</label>
          <small id="smoothingFactorHelpText" class="form-text text-muted">
            <span v-if="smoothingFactor > 0">
              Data points will be averaged with the nearest {{smoothingFactor}}% of other points.
            </span>
            <span v-else>
              No smoothing will be applied.
            </span>
          </small>
          <input type="range"
                 class="form-control-range"
                 min="0" max="10"
                 @change="graphResults"
                 v-model="smoothingFactor"
                 id="formControlRange">
        </div>
      </div>
    </div>
    <div class="graph">
      <div class="container graph-container">
        <line-example :chartData="chartData"
                      :options="chartOptions"
                      ref="chart"/>
      </div>
    </div>
  </div>
</template>

<script>
  import LineExample from './LineChart.vue';
  import LoadingButton from '../vue-shared/loading-button.vue';
  import debounce from 'lodash.debounce';

  export default {
    name: 'Main',
    components: {LineExample, LoadingButton},
    beforeMount() {
      this.jurisdictions = [["*", "Wildcard"]].concat(snippets.jurisdictions);  // eslint-disable-line
      for (const[k, v] of this.jurisdictions)
        this.jurisdictionLookup[k] = v;
      this.urls = urls;  // eslint-disable-line
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
    },
    data: function () {
      return {
        chartData: {datasets: []},
        chartNeedsRerender: false,
        rawData: null,
        textToGraph: "apple pie, baseball",
        minYear: 1800,
        maxYear: 2018,
        minPossible: 1640,
        maxPossible: 2018,
        smoothingFactor: 0,
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
                let label = data.datasets[tooltipItem.datasetIndex].label || '';
                if (label)
                  label += ': ';
                if (this.percentOrAbs === "percent") {
                  label += tooltipItem.yLabel.toPrecision(3) + "% of";
                }else {
                  label += tooltipItem.yLabel;
                }
                label += this.countType === "count" ? " instances" : " cases";
                return label;
              }
            }
          }
        },
      }
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
          q: this.textToGraph
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
        if (query.q)
          this.textToGraph = this.$route.query.q;

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

        this.showLoading = true;
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
          // merge results into single dict for processing, so we can find correct year range
          // const mergedResults = Object.assign({}, ...allResults.filter(result => result !== null));
          // if (Object.keys(mergedResults).length === 0)
          //   return;

          // display results
          const rawData = this.parseResponse(results);
          if (Object.keys(rawData.results).length === 0)
            return;
          this.rawData = rawData;
          this.graphResults();
          this.showLoading = false;
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
    },
  }
</script>
