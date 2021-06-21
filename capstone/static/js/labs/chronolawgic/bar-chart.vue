<script>
import {Bar, mixins} from 'vue-chartjs'
import {EventBus} from "./event-bus";

export default {
  name: "BarChart",
  extends: Bar,
  mixins: [mixins.reactiveProp],
  watch: {
    stats() {
      this.$parent.fillChartData();
    },
    chartData: function () {
      this.renderChart(this.chartData, this.options);
    }
  },
  computed: {
    stats() {
      return this.$store.getters.stats;
    }
  },

  data() {
    return {
      options: {
        legend: {
          position: 'bottom',
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
          xAxes: [{
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
  beforeMount() {
    this.renderChart(this.chartData, this.options)
  }
}
</script>
