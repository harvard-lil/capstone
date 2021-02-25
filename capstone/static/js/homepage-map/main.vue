<template>
  <div class="map-section m-0 pt-0 bg-gradient">
    <div class="d-block d-md-none d-lg-none d-xl-none bg-gradient small-screen-map-section pb-5">
      <div class="row pt-5 top-numbers-row">
        <div class="col-4 offset-2 p-0">
          <p class="bignumber">{{(total_cases/1000000).toFixed(1)}}</p>
        </div>
        <div class="col-4 pt-4">
          <div class="pt-2 pt-sm-4 vseparator">
            <span class="million">Million</span><br>
            <span class="uniquecases">
              Unique cases
            </span>
          </div>
        </div>
      </div>
      <div class="row p-0 mb-3 mb-sm-4">
        <div class="col-8 offset-2 p-0 mt-0 mb-0 vseparator">
        </div>
      </div>

      <div class="row">
        <div class="col-4 offset-2 p-0">
          <div class="sixtwentyseven">{{total_reporters}}</div>
        </div>
        <div class="col-4 p-0">
          <div class="fortym pl-3">{{(total_pages/1000000).toFixed(0)}}M</div>
        </div>
      </div>
      <div class="row">
        <div class="col-4 offset-2 p-0">
          <div class="bottom-text bottom-text-border pl-1 pt-4">Reporters</div>
        </div>
        <div class="col-6 p-0">
          <div class="bottom-text pt-4 pl-2">Pages scanned</div>
        </div>
      </div>


    </div>
    <div class="d-none d-md-block d-lg-block d-xl-block pt-5">
      <div class="row top-section-row">
        <div class="col-1 text-right p-3 d-none d-lg-block">
          <img aria-hidden="true" :src='`${urls.static}img/white-arrow-right.svg`'>
        </div>
        <div class="col-4 offset-1 offset-lg-0">
          <h2 class="section-title p-0">
            Our data
          </h2>
        </div>
      </div>
      <div class="row content-row">
        <div class="col-3 offset-md-1 pr-3">

          <div class="boxcontainer text-white state-numbers-boxcontainer mt-2 mb-4">
            <div class="boxcontainer-body bg-black p-3 pt-2 pb-2">
              <h5 class="boxcontainer-title pb-1 jur_name">
                {{ hoveredSlug ? jurNameForSlug(hoveredSlug) : "State and Federal Totals" }}
              </h5>

              <div class="number-set mt-3 p-0">
                <p class="boxcontainer-text figure mb-0 num_cases">{{ caseCount() }}</p>
                <p class="boxcontainer-text label">Unique cases</p>
              </div>

              <div class="number-set d-lg-block d-md-none p-0">
                <p class="boxcontainer-text figure mb-0 num_reporters">{{ reporterCount() }}</p>
                <p class="boxcontainer-text label">Reporters</p>
              </div>

              <div class="number-set p-0">
                <p class="boxcontainer-text figure mb-0 num_pages">{{ pageCount() }}</p>
                <p class="boxcontainer-text label">Pages scanned</p>
              </div>

              <div aria-live="polite" class="sr-only">
                {{ caseCount() }} cases. {{ reporterCount() }} reporters. {{ pageCount() }} pages.
              </div>

            </div>
            <div class="boxcontainer-body bg-black p-3 pt-2">
              <h5 class="boxcontainer-title pb-1 federal">Federal Totals</h5>

              <div class="number-set">
                <p class="boxcontainer-text figure mb-0">{{ federal_cases.toLocaleString() }}</p>
                <p class="boxcontainer-text label">Unique cases</p>
              </div>

              <div class="number-set d-lg-block d-md-none">
                <p class="boxcontainer-text figure mb-0">{{ federal_reporters.toLocaleString() }}</p>
                <p class="boxcontainer-text label">Reporters</p>
              </div>

              <div class="number-set">
                <p class="boxcontainer-text figure mb-0">{{ federal_pages.toLocaleString() }}</p>
                <p class="boxcontainer-text label">Pages scanned</p>
              </div>
            </div>
          </div>

        </div>
        <div class="col-7">
          <div class="map bg-transparent pl-5">
            <a href="#section-dive-in"
               class="skip">Skip map</a>
            <USMap @mouseover="mapMouseover" @mouseleave="mapMouseleave" @focusin="mapMouseover" tabindex="" />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
  import USMap from '../../../capweb/templates/includes/usa_territories_white.svg';

  export default {
    components: {
      USMap,
    },
    name: 'Main',
    beforeMount: function () {
      // get variables from Django template
      this.urls = urls;  // eslint-disable-line
      this.jurData = jurData;  // eslint-disable-line
      
      // calculate totals based on jurData
      this.total_cases = 0;
      this.total_reporters = 0;
      this.total_pages = 0;
      for (const [k, v] of Object.entries(this.jurData)) {
        this.total_cases += v['case_count'];
        this.total_reporters += v['reporter_count'];
        this.total_pages += v['page_count'];
        if (k === 'us') {
          this.federal_cases = v['case_count'];
          this.federal_reporters = v['reporter_count'];
          this.federal_pages = v['page_count'];
        }
      }
    },
    mounted() {
      for (const stateLink of document.getElementsByClassName('state-link')) {
        stateLink.setAttribute("href", this.urls.jurisdiction.replace("JURISDICTION", stateLink.id));
      }
    },
    data() {
      return {
        hoveredSlug: null,
      }
    },
    methods: {
      mapMouseover(event) {
        const target = event.target;
        if (target.classList.contains('state')) {
          this.hoveredSlug = target.parentElement.id;
        } else if (target.classList.contains('state-link')) {
          this.hoveredSlug = target.id;
        } else {
          this.hoveredSlug = null;
        }
      },
      mapMouseleave() {
       this.hoveredSlug = null;
      },
      jurNameForSlug(slug) {
        return document.getElementById(slug).getAttribute('aria-label');
      },
      caseCount() {
        return (this.hoveredSlug ? this.jurData[this.hoveredSlug].case_count : this.total_cases).toLocaleString()
      },
      reporterCount() {
        return (this.hoveredSlug ? this.jurData[this.hoveredSlug].reporter_count : this.total_reporters).toLocaleString()
      },
      pageCount() {
        return (this.hoveredSlug ? this.jurData[this.hoveredSlug].page_count : this.total_pages).toLocaleString()
      },
    },
  }
</script>