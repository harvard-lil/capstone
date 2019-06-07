<script>
  import {Line, mixins} from 'vue-chartjs'

  export default {
    extends: Line,
    mixins: [mixins.reactiveProp],
    props: ["options"],
    methods: {
      fullRerender(chartData, options) {
        // this exists only as a workaround for non-reactive properties that need to be updated,
        // currently just yAxisID -- https://github.com/apertureless/vue-chartjs/issues/177
        if (this.$data._chart)
          this.$data._chart.destroy();
        this.renderChart(chartData, options)
      }
    }
  }
</script>
