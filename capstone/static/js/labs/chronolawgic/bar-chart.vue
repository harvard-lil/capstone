<script>
import {Bar, mixins} from 'vue-chartjs'


export default {
  name: "BarChart",
  extends: Bar,
  mixins: [mixins.reactiveProp],
  watch: {
    firstYear() {
      console.log('watch, firstYear', this.firstYear)
      this.$parent.fillChartData();
      // return this.firstYear;
    },
    lastYear() {
      console.log('watch, lastyear', this.lastYear)
      this.$parent.fillChartData();
      // return this.lastYear;
    },
    chartData: function () {
      console.log('bar-chart.vue, watching chartData')
      this.renderChart(this.chartData, this.options);
    }
  },
  computed: {
    firstYear() {
      // console.log('computed', this.$store.getters.firstYear)
      return this.$store.getters.firstYear;
    },
    lastYear() {
      // console.log('computed', this.$store.getters.lastYear)
      return this.$store.getters.lastYear;
    }
  },

  data() {
    return {
      options: {
        legend: {
          position: 'bottom',
        },
        animation: {
          duration: 0 // disable animation
        },
        responsive: true,
        maintainAspectRatio: false,
        barPercentage: 1,
        categoryPercentage: 1,
        scales: {

          xAxes: [
            {
              display: true,
              stacked: true,
              ticks: {
                beginAtZero: true,
              },
              barThickness: 2,

              gridLines: {
                display: false,
              },
            }],
          yAxes: [{
            display: false,
            stacked: true,
            ticks: {
              beginAtZero: true,
            },

            borderColor: '#ffffff',
            gridLines: {
              display: false,
            },
          }],
          x: {
            grid: {
              drawBorder: false,
              borderColor: '#ffffff'
            },
          },
          y: {
            grid: {
              drawBorder: false,
              borderColor: '#ffffff'
            },
          }
        }
      },
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
    getRandomInt() {
      return Math.floor(Math.random() * (50 - 5 + 1)) + 5
    },

    // fillData() {
    //
    // }

  },
  beforeMount() {
    // this.addPlugin(horizonalLinePlugin)
  },
  afterMount() {
    this.renderChart(this.chartData, this.options)
    // this.fillChartData();
    // console.log('mounted')
    // const firstYear = this.$store.getters.firstYear;
    // const finalYear = this.$store.getters.lastYear;
    //
    // this.fillData()
    // setInterval(() => {
    //   this.fillData()
    // }, 5000)
    //   console.log("mounted", this.firstYear, this.lastYear)
  }
}
</script>
