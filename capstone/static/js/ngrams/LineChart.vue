<script>
  import {Line, mixins} from 'vue-chartjs'

  const {reactiveProp} = mixins;

  export default {
    extends: Line,
    props: ['chartData', 'percentOrAbs', 'countType', 'smoothingWindow'],
    mixins: [reactiveProp],
    data() {
      return {
        options: {
          responsive: true,
          maintainAspectRatio: false,
          legend: {
            labels: {
              boxWidth: 20,
              usePointStyle: true,
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
            }]
          },
          tooltips: {
            callbacks: {
              title: (tooltipItem, data) => {
                /* format tooltip title to include date range when smoothing is on */
                const label = tooltipItem[0].label;
                if (!this.smoothingWindow)
                  return label;
                const startRange = Math.max(data.labels[0], Number(label)-this.smoothingWindow);
                const endRange = Math.min(data.labels[data.labels.length-1], Number(label)+this.smoothingWindow);
                return `${startRange}-${endRange}`;
              },
              label: (tooltipItem, data) => {
                /*
                  format tooltip text based on percentOrAbs and countType,
                  like "term: X% of instances" or "term: Y cases"
                */
                let label = data.datasets[tooltipItem.datasetIndex].label || '';
                if (label)
                  label += ': ';
                if (this.percentOrAbs === "percent") {
                  label += tooltipItem.yLabel.toPrecision(3) + "% of";
                }else {
                  label += tooltipItem.yLabel;
                }
                label += this.countType === "count" ? " instances" : " cases";
                return label;
              }
            }
        }
        }
      }
    }
  }
</script>
