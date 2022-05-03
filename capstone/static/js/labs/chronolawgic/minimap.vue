<template>
  <div class="chart-container">
    <h6>Timeline overview</h6>
    <div class="chart">
      <bar-chart :chartData="chartData" options="options" :width="100" :height="150"/>
    </div>
    <p class="small">Click on chart to travel to date</p>
  </div>
</template>
<script>
import BarChart from './bar-chart.vue';

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
    fillChartData() {
      let firstYear = this.$store.getters.firstYear ? this.$store.getters.firstYear : 1900
      let lastYear = this.$store.getters.lastYear ? this.$store.getters.lastYear : 2000;
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
            backgroundColor: '#000000',
            tension: 0.1,
            borderWidth: 0,
            data: this.$store.getters.stats[1]
          },
        ]
      }
    }
  },
  mounted() {
    this.fillChartData();
  },
}
</script>
