<template>
  <div class="row witchcraft-content">
    <div v-if="mounted" class="col-md-3 col-sm-12 col-xs-12">
      <div class="witchcraft-info-box">
        <div class="witchcraft-figures">

          <div class="form-group title jur_name">
            <label for="hoveredJurSelect">Selected jurisdiction:</label>
            <select class="form-control" id="hoveredJurSelect" v-model="hoveredSlug">
              <option disabled value="">Select one, or use the map</option>
              <option v-for="jur in jurisdictions" :key="jur[0]" v-bind:value="jur[0]">{{jur[1]}}</option>
            </select>
          </div>
          <div>
            <span class="title num_appearances">{{ appearanceCount(hoveredSlug) }}</span> appearances
            in <span class="title num_cases">{{ caseCount(hoveredSlug) }}</span> cases
          </div>
        </div>
        <div class="item-set excerpts">Excerpts:</div>
        <ol class="excerpt-box">
          <li v-for="item in results[hoveredSlug]" class="excerpt-item"> <!-- eslint-disable-line vue/require-v-for-key -->
            "...{{item.context}}..." <a :href="item.url">{{item.name}}</a><span class="excerpt-date"> {{item.decision_date}} </span>
          </li>
        </ol>
        <a class="btn btn-inverse api-list-link"
           target="_blank"
           :href="`${urls.caseApi}?jurisdiction=${hoveredSlug}&search=witchcraft`">
          <span class="jur_name_small">{{jurisdictionsBySlug[hoveredSlug]}}</span> in API
        </a>
      </div>
    </div>

    <div class="col-lg-9 col-md-12 col-xs-12" aria-label="United States map showing frequency of the term 'witchcraft' in caselaw">
      <div aria-hidden="true">
        <USMap @click="mapClick" @mouseover="mapMouseover" />
      </div>
    </div>
  </div>
</template>

<script>
  import USMap from '../../../capweb/templates/includes/usa_territories_white.svg';
  import { witchcraft_results } from './witchcraft-data.js';

  const sum = (arr) => arr.reduce((a, b) => a + (b || 0), 0);
  const getRandomNum = (min, max) => Math.round(Math.random() * (max - min) + min);

  export default {
    name: 'Main',
    components: {
      USMap,
    },
    beforeMount: function () {
      // get variables from Django template
      this.urls = urls;  // eslint-disable-line
      this.results = witchcraft_results;
    },
    mounted() {
      this.jurisdictions = [];
      this.jurisdictionsBySlug = {};
      for (const stateLink of document.getElementsByClassName('state-link')) {
        const slug = stateLink.id;
        if (!witchcraft_results[slug])
          continue;
        const name = stateLink.ariaLabel;
        this.jurisdictionsBySlug[slug] = name;
        this.jurisdictions.push([slug, name]);
        stateLink.style.fillOpacity = this.appearanceCount(slug) / 45;
        stateLink.style.fill = 'orange';
      }
      this.hoveredSlug = this.jurisdictions[getRandomNum(0, this.jurisdictions.length)][0];
      this.mounted = true;
    },
    data() {
      return {
        jurisdictions: [],
        hoveredSlug: null,
        mounted: false,
        doMouseover: true,
      }
    },
    methods: {
      appearanceCount(slug) {
        if (!slug) return 0;
        return sum(this.results[slug].map(c => c.times_appeared));
      },
      caseCount(slug) {
        if (!slug) return 0;
        return this.results[slug].length;
      },
      mapSelect(event) {
        const target = event.target;
        if (target.classList.contains('state')) {
          this.hoveredSlug = target.parentElement.id;
        }
      },
      mapClick(event) {
        this.doMouseover = false;
        this.mapSelect(event);
      },
      mapMouseover(event) {
        if (this.doMouseover)
          this.mapSelect(event);
      },
    },
  }
</script>
