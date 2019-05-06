<template>
  <div>
    <div class="row">
      <h1 class="page-title">
        Ngrams
      </h1>

    </div>
    <div class="row">
      <input class="col-4" placeholder="Your text here" v-model="textToGraph">
      <span class="col-4"><button v-on:click="createGraph">Graph</button></span>
      <button class="dropdown-toggle add-field-button btn-secondary col-4"
              type="button"
              id="jurisdictions"
              data-toggle="dropdown"
              aria-haspopup="true"
              aria-expanded="false">
        Select jurisdictions
      </button>

      <div class="dropdown dropdown-menu col-4" aria-labelledby="jurisdictions">

        <button class="dropdown-item" type="button"
                v-on:click="toggleJur(jurisdiction)"
                :class="{active: selectedJurs.indexOf(jurisdiction) > -1}"
                v-for="jurisdiction in jurisdictions" :key="jurisdiction[0]">
          {{jurisdiction[1]}}
        </button>
      </div>
      <div class="row">
        <div class="selected-jurs">
          <span class="small selected-jur" v-on:click="toggleJur(jur)" v-for="jur in selectedJurs">
            {{jur[1]}}
          </span>
        </div>
      </div>
    </div>
    <div class="graph">
      <div class="container">
        <line-example :chartData="chartData">
        </line-example>
      </div>
    </div>

  </div>
</template>

<script>
  import LineExample from './LineChart.vue';
  import axios from 'axios';

  export default {
    name: 'Main',
    components: {
      'line-example': LineExample
    },
    beforeMount() {
      this.jurisdictions = snippets.jurisdictions;  // eslint-disable-line
    },
    data: function () {
      return {
        chartData: null,
        textToGraph: "",
        minYear: 1640,
        maxYear: 2018,
        jurisdictions: {},
        selectedJurs: [],
      }
    },
    methods: {
      range(start, stop, step = 1) {
        return Array(Math.ceil((stop - start) / step)).fill(start).map((x, y) => x + y * step)
      },
      getSelectedJurs() {
        let selected = this.selectedJurs.map(jur => jur[0]);
        return selected;
      },
      createGraph() {
        console.log("text to graph:", this.textToGraph);
        let terms = this.textToGraph.split(",");
        // debugger;
        let years = this.range(1640, 2018);
        console.log("getting years", years);
        this.chartData = {
          labels: years,
          datasets: []
        };
        let jurs = this.getSelectedJurs();
        jurs.splice(0, 0, "");
        let jurs_params = jurs.join("&jurisdiction=");

        for (let idx in terms) {
          let self = this;
          let term = terms[idx];

          axios
              .get("http://api.case.test:8000/v1/ngrams/?&q=" + term + jurs_params)
              .then((resp) => {
                // console.log("getting back results!", )
                // [instance_count, document_count]
                let data = resp.data.results[term];
                let results = [];
                for (let idx in data) {
                  let jur = data[idx];
                  for (let y in years) {
                    let year = years[y];
                    if (results[y]) {
                      if (jur[year]) {
                        results[y] = results[y] + jur[year][0]
                      }
                    } else if (jur[year]) {
                      results[y] = jur[year][0]
                    } else {
                      results[y] = 0;
                    }
                  }

                }
                let newDatasets = self.chartData.datasets;
                newDatasets.push({
                  label: term,
                  borderColor: '#' + (Math.random() * 0xFFFFFF << 0).toString(16),
                  data: results
                });
                self.chartData = {
                  labels: years,
                  datasets: newDatasets
                };
                console.log("getting data:", self.chartData)
              });

        }


      },
      getRandomInt() {
        return Math.floor(Math.random() * (50 - 5 + 1)) + 5
      },
      toggleJur(jurisdiction) {
        if (this.selectedJurs.indexOf(jurisdiction) > -1) {
          this.selectedJurs.splice(this.selectedJurs.indexOf(jurisdiction), 1);
        } else {
          this.selectedJurs.push(jurisdiction);
        }
        console.log("current selected jurs:", this.selectedJurs);
      },
    },
    mounted() {
      // this.createGraph()
    }
  }
</script>
<style scoped>
  .graph {
    font-family: 'Avenir', Helvetica, Arial, sans-serif;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
    text-align: center;
  }

</style>