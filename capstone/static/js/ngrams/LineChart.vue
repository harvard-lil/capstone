<script>
  import {Line, mixins} from 'vue-chartjs'

  const {reactiveProp} = mixins;

  export default {
    extends: Line,
    props: ['chartData', 'options'],
    mixins: [reactiveProp],
    mounted() {
      this.renderChart(this.chartData, this.options)
    }
  }
</script>
