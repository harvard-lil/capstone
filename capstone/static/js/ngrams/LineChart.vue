<script>
  import {Line, mixins} from 'vue-chartjs'

  const {reactiveProp} = mixins;

  export default {
    extends: Line,
    props: ['chartData'],
    mixins: [reactiveProp],
    data() {
      return {
        options: {
          responsive: true,
          maintainAspectRatio: false,
          legend: {
            labels: {
              boxWidth: 20,
            }
          },
          scales: {
            yAxes: [{
              gridLines: {
                color: "rgba(0, 0, 0, 0)",
              },
              ticks: {
                beginAtZero: true,
                callback: function (value) {
                  if (value % 1 === 0) {
                    return value;
                  }
                }
              }
            }],
            xAxes: [{
              gridLines: {
                color: "rgba(0, 0, 0, 0)",
              },
              ticks: {
                beginAtZero: true,
              }
            }]
          }
        }
      }
    },
    mounted() {
      this.renderChart(this.chartData, this.options)
    }
  }
</script>
