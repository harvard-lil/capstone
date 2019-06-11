<script>
  import {Line, mixins} from 'vue-chartjs'

  export default {
    extends: Line,
    mixins: [mixins.reactiveProp],
    props: ["options"],
  }
</script>
