<template>
  <div>
<!-- Stuff to support a future state-detail page:   -->
<!--    <div>-->
<!--      <p>-->
<!--        <label for="choose-state">Get more detail about a state:</label>-->
<!--        <select id="choose-state" @change="detailJurisdiction=$event.target.value">-->
<!--          <option>choose one:</option>-->
<!--          <option v-for="jur in jurisdictions" :value="jur.id">{{jur.name}}</option>-->
<!--        </select>-->
<!--      </p>-->
<!--    </div>-->
<!--    <div v-if="detailJurisdiction">-->
<!--      <p>Total inbound citations: {{totalInbound(detailJurisdiction)}}</p>-->
<!--      <p>Total outbound citations: {{totalOutbound(detailJurisdiction)}}</p>-->
<!--    </div>-->
<!--    <div v-else>-->
    <div>

      <h2>Map view</h2>
      <div class="row">
        <div class="col-lg-3 col-md-12">
          <div class="form-group">
            <label for="hoveredJurSelect">Selected jurisdiction:</label>
            <select class="form-control" id="hoveredJurSelect" v-model="hoveredJur">
              <option disabled value="">Select one, or hover on the map</option>
              <option v-for="jur in jurisdictions" v-bind:value="jur">{{jur.name_long}}</option>
            </select>
          </div>
          <div class="form-check">
            <input class="form-check-input" type="radio" id="mapDirectionInbound" value="inbound" v-model="mapDirection">
            <label class="form-check-label" for="mapDirectionInbound">Inbound citations</label>
          </div>
          <div class="form-check">
            <input class="form-check-input" type="radio" id="mapDirectionOutbound" value="outbound" v-model="mapDirection">
            <label class="form-check-label" for="mapDirectionOutbound">Outbound citations</label>
          </div>
          <div id="hovered-map-message">
            <span v-if="hoveredJur">
              Darker states are more likely to {{mapDirection === "inbound" ? "cite to" : "be cited by"}} {{hoveredJur.name_long}}.
            </span>
            <span v-else>
              Hover over a state to see what other states {{mapDirection === "inbound" ? "most often cite it" : "it most often cites"}}.
            </span>
          </div>
        </div>
        <div class="col-lg-9 col-md-12" aria-label="United States map showing frequency of citations from one jurisdiction to another by color">
          <div aria-hidden="true">
            <USMap @mouseover="mapMouseover" @mouseleave="mapMouseleave" class="map" />
          </div>
        </div>
      </div>

      <h2>Grid view</h2>
      <p>
        This grid shows what percentage of the citations <i>by</i> each state on the left are <i>to</i> each state
        on the top. For example, the square in the row marked "Alaska" and column marked "Cal." indicates that
        2.5% of all citations extracted from Alaska cases are to California cases.
        <a href="#" download="cite-grid.csv" @click="csvDownloadClicked" @contextmenu="csvDownloadClicked">Download CSV</a>.
      </p>
      <div>
        Coloring of each square is logarithmic to emphasize the range between 0 and 10%:<br>
        0%
        <div style="display: inline-block; background-color: white">
          <span v-bind:key="i" v-for="i in 20" :style="{backgroundColor: percentageColor((i-1)/2), width: '1em', display: 'inline-block'}" :title="`${(i-1)/2}%`">&nbsp;</span>
        </div>
        10%
      </div>
      <p>
        Hover over a grid square for details:
      </p>
      <div class="table-scroll">
        <table v-if="dataLoaded">
          <tr>
            <th :class="{'top-header': true, 'left-header': true, disabled: selfDisabled}"
                @click="selfDisabled = !selfDisabled"
            >
              <div v-if="hoveredGridMessage" class="hovered-grid-message">{{hoveredGridMessage}}</div>
              <div>Self</div>
            </th>
            <th v-for="toJur in jurisdictions"
                :key="toJur.id"
                :class="{rotate: true, 'top-header': true, disabled: disabled[toJur.id]}"
                @click="toggleJurisdiction(toJur)"
                scope="col"
            >
              <div>{{toJur.name}}</div>
            </th>
          </tr>
          <tr v-for="fromJur in jurisdictions" :key="fromJur.id">
            <th scope="row" class="left-header">{{fromJur.name}}</th>
            <td v-for="toJur in jurisdictions"
                :key="toJur.id"
                :style="{backgroundColor: countColor(fromJur, toJur)}"
                :title="hoverText(fromJur, toJur)"
                @mouseover="hoveredGridMessage=hoverText(fromJur, toJur)"
                @mouseleave="hoveredGridMessage=null"
            >
            </td>
          </tr>
        </table>
      </div>
    </div>
  </div>
</template>

<script>
  import csvStringify from 'csv-stringify/lib/sync';
  import {apiQuery} from '../api';
  import USMap from '../../../capweb/templates/includes/usa_territories_white.svg';

  /* eslint-disable */
  // const deepCopy = (value) => JSON.parse(JSON.stringify(value));
  const toHashMap = (a,f) => a.reduce((a,c)=> (a[f(c)]=c,a),{});
  const sum = (arr) => arr.reduce((a, b) => a + (b || 0), 0);

  export default {
    name: 'Main',
    components: {
      USMap,
    },
    async mounted() {
      this.jurisdictions = await this.getJSON('jurisdictions.json');
      for (const j of this.jurisdictions)
        j.id = j.id.toString();
      this.jurisdictionsById = toHashMap(this.jurisdictions, jur=>jur.id);
      this.jurisdictionsBySlug = toHashMap(this.jurisdictions, jur=>jur.slug);
      this.jurisdictionsNotOnMap = toHashMap(this.jurisdictions.filter(jur=>document.getElementById(jur.slug)===null),jur=>jur.id);
      this.totals = await this.getJSON('totals.json');
      // this.totalsByYear = await this.getJSON('totals_by_year.json');
      this.dataLoaded = true;
    },
    data() {
      return {
        jurisdictions: null,
        totals: null,
        totalsByYear: null,
        selfDisabled: false,
        disabled: {},  //39: true},
        dataLoaded: false,
        detailJurisdiction: null,
        hoveredJur: null,
        mapDirection: "inbound",
        hoveredGridMessage: null,
      }
    },
    watch: {
      hoveredJur: function (focusedJur) {
        if (focusedJur) {
          // when hovering over a jurisdiction in the map, set opacity of all other jurisdictions
          const id = focusedJur.id;
          const focusedEl = document.getElementById(focusedJur.slug);
          focusedEl.style.fillOpacity = 1;
          focusedEl.classList.add("focused");
          const countFunction = this.mapDirection === "inbound" ? this.inboundCounts : this.outboundCounts;
          const maxCount = Math.max(...countFunction(id, this.jurisdictionsNotOnMap));
          for (const jur of this.jurisdictions) {
            if (jur.id === id)
              continue;
            const count = this.mapDirection === "inbound" ? this.totals[jur.id][id] : this.totals[id][jur.id];
            const jurEl = document.getElementById(jur.slug);
            if (!jurEl)
              continue;
            jurEl.style.fillOpacity = count/maxCount;
            jurEl.classList.remove("focused");
          }
        }
      }
    },

    methods: {
      async getJSON(fileName) {
        return await apiQuery("/download/citation_graph/2020-05-08/aggregations/"+fileName);
      },
      citePercentage(fromJur, toJur) {
        // disabling this for now -- allows vertical jurisdictions in grid to be removed
        // less useful with logPercentage() coloring
        // const disabled = {...this.disabled};
        // if(this.selfDisabled)
        //   disabled[fromJur.id] = true;
        // if (disabled[toJur.id])
        //   return '';
        // const toSubtract = sum(Object.keys(disabled).map((id) => this.totals[fromJur.id][id]));
        // const denominator = this.jurisdictionsById[fromJur.id].cites - toSubtract;
        const denominator = this.jurisdictionsById[fromJur.id].cites;
        let percentage = 0;
        if (denominator)
          percentage = (this.totals[fromJur.id][toJur.id] || 0) / denominator * 100;
        return percentage ? percentage.toFixed(1) : 0;
      },
      countColor(fromJur, toJur) {
        // return color for citation count from fromJur to toJur
        return this.percentageColor(this.citePercentage(fromJur, toJur));
      },
      percentageColor(x) {
        // convert a percentage between 0 and 100 to a color, log normalized
        return `rgba(44, 96, 255, ${this.logPercentage(x)}%)`;
        // return `hsl(0,0%,${100-this.logPercentage(x)}%)`;
      },
      hoverText(fromJur, toJur) {
        let percentage = this.citePercentage(fromJur, toJur);
        return `${this.jurisdictionsById[fromJur.id].name} cites ${this.jurisdictionsById[toJur.id].name} ${percentage}%`;
      },
      toggleJurisdiction(jur) {
        if (this.disabled[jur.id])
          this.$delete(this.disabled, jur.id);
        else
          this.$set(this.disabled, jur.id, true);
      },
      inboundCounts(id, ignore) {
        if (!ignore)
          ignore = {};
        return Object.entries(this.totals)
          .filter(([k, v]) => k !== id && !ignore[k] && v[id] > 0)
          .map(([k, v]) => v[id]);
      },
      outboundCounts(id, ignore) {
        if (!ignore)
          ignore = {};
        return Object.entries(this.totals[id])
          .filter(([k, v]) => k !== id && !ignore[k] && v > 0)
          .map(([k, v]) => v);
      },
      totalInbound(id) {
        return sum(this.inboundCounts(id));
      },
      totalOutbound(id) {
        return sum(this.outboundCounts(id));
      },
      mapMouseover(event) {
        if (!this.dataLoaded)
          return;
        const target = event.target;
        if (target.classList.contains('state')) {
          this.hoveredJur = this.jurisdictionsBySlug[target.parentElement.id];
        }
      },
      mapMouseleave(event) {
       // this.hoveredJur = null;
      },
      logPercentage(x) {
        if (x<.1)
          return x;
        return (Math.log(x) - Math.log(.1)) / (Math.log(100) - Math.log(.1)) * 100;
      },
      csvDownloadClicked(event) {
        /* when the Download url is clicked/right-clicked/touched, intercept the event and fill in the correct data for download */
        let payload = [];
        payload.push(["", ...this.jurisdictions.map((jur)=>jur.name_long)]);
        for (const fromJur of this.jurisdictions) {
          payload.push([fromJur.name_long, ...this.jurisdictions.map((toJur)=>this.citePercentage(fromJur, toJur))]);
        }
        payload = "data:text/csv;base64," + btoa(csvStringify(payload));
        event.currentTarget.href = payload;
      },
    },
  }
</script>

<style lang="scss" scoped>
  .map {
    .state-link {
      &.focused .state {
        fill: #EDA633;
      }
    }
    .state {
      stroke: black;
      stroke-width: .5;
      cursor: pointer;
      pointer-events: all;
      fill: #2C60FF;
    }
  }
  .hovered-grid-message {
    position: absolute;
    left: 0;
    top: 0;
    background-color: white;
    padding: .2em;
    border: 1px black solid;
  }
  #hovered-map-message {
    margin-top: 1em;
    font-weight: bold;
  }
</style>