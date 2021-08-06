<template>
  <main id="most-cited">
    <div class="info-container">
      <div class="header">
        <h1 id="selected-state">
          {{ selectedState }}
          <template v-if="selectedState && selectedState !== 'Overall' && !errors">
            <button class="btn btn-primary btn-close" @click="getOverall()">
              <close-icon></close-icon>
            </button>
          </template>
        </h1>
        <input type="number" class="selected-year" :min="minYear" :max="maxYear" v-model="year" @change="getYearData">
      </div>
      <div id="state-citations">
        <template v-if="errors">
          {{ errors }}
          <br/>
        </template>

        <!--If state is clicked-->
        <template v-else-if="selectedState !== 'Overall'">
          <b>Top cited {{ selectedState }} cases in the year {{ year }}</b>
          <br/>
          <ul v-for="(jur_cases, name) in cases" :class="{'active': cleanJurisdictionName(name) === selectedSlug}"
              v-bind:key="name">
            <li v-for="(Case, idx) in jur_cases" :class="name" class="states-info" v-bind:key="idx">
              <!--Name of case (linked to case on CAP)-->
              <a :href="Case[Object.keys(Case)[0]][2]">
                <b>{{ Object.keys(Case)[0] }}</b>
              </a>
              <!--decision date if available-->
              <template v-if="Case[Object.keys(Case)[0]][3]"> ({{ Case[Object.keys(Case)[0]][3] }})</template>
              <!--how many times cited-->
              cited {{ Case[Object.keys(Case)[0]][1] }} times
            </li>
          </ul>
        </template>

        <!--If overall stats are shown-->
        <template v-else>
          <b>Top cited state cases in United States in the year {{ year }}</b>
          <br/>
          <ul v-for="overallCase in overallCases" v-bind:key="Object.keys(overallCase)[0]" class="active">
            <li v-for="(Case, name) in overallCase" v-bind:key="name">
            <!--Name of case (linked to case on CAP)-->
              <a :href="Case[2]">
                <b>{{ name }}</b>
              </a>
              <!--decision date if available-->
              <template v-if="Case[3]"> ({{ Case[3] }}, </template>
              <!--name of decision jurisdiction and how many times case is cited-->
              <b v-if="Case[4]">{{ translation[cleanJurisdictionName(Case[4])] }})</b> cited {{ Case[1] }} times
            </li>
          </ul>
        </template>
      </div>
    </div>
    <div class="map-container">
      <p>The darker the color the more citations a jurisdiction receives in the selected year.</p>
      <div class="map bg-transparent">
        <a href="#section-dive-in"
           class="skip">Skip map</a>
        <USMap @click="mapChoose" tabindex=""/>
      </div>
    </div>

  </main>
</template>

<script>
import USMap from '../../../../capweb/templates/includes/usa_territories_white.svg';
import CloseIcon from '../../../../static/img/icons/close.svg';
import axios from "axios";

export default {
  name: 'Admin',
  components: {
    USMap,
    CloseIcon,
  },
  data() {
    return {
      year: 2000,
      selectedSlug: '',
      selectedState: 'Overall',
      stateCitation: '',
      cases: undefined,
      overallCases: undefined,
      errors: '',
    }
  },
  computed: {
    minYear() {
      return 1806
    },
    maxYear() {
      return 2017
    },
    all_jurisdictions() {
      return [
        "Ala.", "Alaska", "Ariz.", "Ark.", "Cal.", "Colo.", "Conn.", "D.C.", "Del.", "Fla.", "Ga.", "Haw.", "Idaho", "Ill.", "Ind.", "Iowa", "Kan.", "Ky.", "La.", "Mass.", "Md.", "Me.", "Mich.", "Minn.", "Miss.", "Mo.", "Mont.", "N. Mar. I.", "N.C.", "N.D.", "N.H.", "N.J.", "N.M.", "N.Y.", "Navajo Nation", "Neb.", "Nev.", "Ohio", "Okla.", "Or.", "P.R.", "Pa.", "R.I.", "S.C.", "S.D.", "Tenn.", "Tex.", "Tribal", "Utah", "V.I.", "Va.", "Vt.", "W. Va.", "Wash.", "Wis.", "Wyo."
      ]
    },
    translation() {
      return {
        "ala": "Alabama",
        "alaska": "Alaska",
        "ariz": "Arizona",
        "ark": "Arkansas",
        "cal": "California",
        "colo": "Colorado",
        "conn": "Connecticut",
        "dc": "District of Columbia",
        "dakota-territory": "Dakota Territory",
        "del": "Delaware",
        "fla": "Florida",
        "ga": "Georgia",
        "haw": "Hawaii",
        "idaho": "Idaho",
        "ill": "Illinois",
        "ind": "Indiana",
        "iowa": "Iowa",
        "kan": "Kansas",
        "ky": "Kentucky",
        "la": "Louisiana",
        "mass": "Massachusetts",
        "md": "Maryland",
        "me": "Maine",
        "mich": "Michigan",
        "minn": "Minnesota",
        "miss": "Mississippi",
        "mo": "Missouri",
        "mont": "Montana",
        "n-mar-i": "Northern Mariana Islands",
        "nc": "North Carolina",
        "nd": "North Dakota",
        "nh": "New Hampshire",
        "nj": "New Jersey",
        "nm": "New Mexico",
        "ny": "New York",
        "neb": "Nebraska",
        "nev": "Nevada",
        "ohio": "Ohio",
        "okla": "Oklahoma",
        "or": "Oregon",
        "pr": "Puerto Rico",
        "pa": "Pennsylvania",
        "ri": "Rhode Island",
        "sc": "South Carolina",
        "sd": "South Dakota",
        "tenn": "Tennessee",
        "tex": "Texas",
        "tribal": "Tribal Jurisdictions",
        "utah": "Utah",
        "vi": "Virgin Islands",
        "va": "Virginia",
        "vt": "Vermont",
        "w-va": "West Virginia",
        "wash": "Washington",
        "wis": "Wisconsin",
        "wyo": "Wyoming"
      }
    },
  },
  methods: {
    mapChoose(event) {
      const target = event.target;
      if (target.classList.contains('state')) {
        this.selectedSlug = target.parentElement.id;
        this.selectedState = this.translation[this.selectedSlug];
      }
    },
    mapMouseleave() {
      this.selectedSlug = null;
    },
    getYearData() {
      axios.get(`/labs/most-cited/data/${this.year}`)
          .then((resp) => {
            return resp.data
          }).then((data) => {
        this.errors = '';
        let not_included_jurs = this.all_jurisdictions.filter(x => !Object.keys(data).includes(x));
        let highest_val = 0
        for (const jur in data) {
          if (data[jur][0] > highest_val) {
            highest_val = data[jur][0]
          }
        }
        let cleaned_jur = "";
        this.cases = {};
        let val, count;
        for (const jur in data) {
          cleaned_jur = this.cleanJurisdictionName(jur);
          count = data[jur][0]
          this.cases[jur] = data[jur].slice(1);
          val = count / highest_val
          this.setFillAndAttribute(cleaned_jur, val, count)
        }
        for (let i = 0; i < not_included_jurs.length; i++) {
          cleaned_jur = this.cleanJurisdictionName(not_included_jurs[i]);
          this.setFillAndAttribute(cleaned_jur, "0", "0")
        }
      }).catch((err) => {
        let cleaned_jur;
        for (let i = 0; i < this.all_jurisdictions.length; i++) {
          cleaned_jur = this.cleanJurisdictionName(this.all_jurisdictions[i]);
          this.setFillAndAttribute(cleaned_jur, "0", "0")
        }
        this.errors = "Information is not available for this year"
        this.selectedState = '';
        return err
      })
    },
    getOverall() {
      this.selectedState = 'Overall'
      axios.get(`/labs/most-cited/overall-data/${this.year}`)
          .then((resp) => {
            return resp.data.response
          }).then((data) => {
        this.overallCases = data;
      })
    },
    cleanJurisdictionName(name) {
      if (!name) return
      return name.toLowerCase().split('.').join('').split(' ').join('-')
    },
    setFillAndAttribute(jur, colorValue, count) {
      try {
        let mapJur = document.getElementById(jur)
        mapJur.children[0].style.fill = `rgba(255, 99, 71, ${colorValue})`
        mapJur.setAttribute('title', count)
      } catch {
        // do nothing, jurisdiction not able to be mapped
      }
    },
  },
  mounted() {
    this.getYearData();
    this.getOverall()
  }
};
</script>

