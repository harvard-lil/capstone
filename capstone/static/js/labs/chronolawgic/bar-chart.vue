<script>
import {Bar, mixins} from 'vue-chartjs'
import { EventBus } from "./event-bus";

export default {
  name: "BarChart",
  extends: Bar,
  mixins: [mixins.reactiveProp],
  watch: {
    firstYear() {
      this.$parent.fillChartData();
    },
    lastYear() {
      this.$parent.fillChartData();
    },
    chartData: function () {
      this.renderChart(this.chartData, this.options);
    }
  },
  computed: {
    firstYear() {
      return this.$store.getters.firstYear;
    },
    lastYear() {
      return this.$store.getters.lastYear;
    }
  },

  data() {
    return {
      options: {
        legend: {
          position: 'bottom',
        },
        plugins: {
          title: {
            display: true,
            text: 'Custom Chart Title',
            padding: {
              top: 10,
              bottom: 30
            }
          }
        },
        onClick: this.handleClick,
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
                autoSkipPadding: 2,
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
    handleClick(evt, array) {
       if (array.length) {
            let position = array[0]._index;
            let activeElement = this.chartData.labels[position]
            EventBus.$emit('goToYear', activeElement)
       }
    }
  },
  afterMount() {
    this.renderChart(this.chartData, this.options)
  }
}
</script>