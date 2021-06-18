<template>
  <div class="container">
    <div class="Chart">
      <bar-chart :chartData="chartData" options="options" :width="100" :height="150"/>
    </div>
  </div>
</template>

<script>
import BarChart from './bar-chart';

export default {
  name: "Minimap",
  components: {
    BarChart
  },
  data() {
    return {
      chartData: {
        labels: [],
        datasets: [
          {
            label: 'Cases',
            backgroundColor: '#f87979',
            data: []
          },
          {
            label: 'Events',
            backgroundColor: '#3d5b96',
            data: []
          }
        ]
      }

    }
  },
  methods: {
    createMapSegments() {
      let segments = 8;
      if (this.lastYear > this.firstYear) {
        let difference = this.lastYear - this.firstYear;
        let segmentsLength = difference / segments;
        console.log(segmentsLength)
        this.minimapSegments = Array(segments).fill({size: 0})
        // console.log('this.minimapSegments', this.minimapSegments)

      }

    },
    fillChartData() {
      let firstYear = this.$store.getters.firstYear ? this.$store.getters.firstYear : 1900
      let lastYear = this.$store.getters.lastYear ? this.$store.getters.lastYear : 2000;
      console.log('fillChartData', firstYear, lastYear)
      this.chartData = {
        labels: Array.from(new Array(lastYear + 1 - firstYear), (x, i) => firstYear + i),
        datasets: [
          {
            label: 'Cases',
            pointRadius: 0,
            backgroundColor: '#f87979',
            tension: 0.1,
            borderWidth: 0,
            data: this.$store.getters.stats[0]
          },
          {
            label: 'Events',
            pointRadius: 0,
            backgroundColor: '#3D5B96',
            tension: 0.1,
            borderWidth: 0,
            data: this.$store.getters.stats[1]
          },
        ]
      }
      console.log('bar-chart::::chartData', this.chartData)
    }
  },

  beforeMount() {
    console.log(this.$store.getters.stats)
    // let lastYear = this.$store.getters.stats[0]
    // let firstYear = this.$store.getters.stats[1]

    console.log(this.chartData)
  }
}
</script>

<style scoped>
.container {
  max-width: 800px;
  margin: 0 auto;
}

.Chart {
  padding: 20px;
  margin: 50px 0;
  border: 1px solid gray;
}
</style>