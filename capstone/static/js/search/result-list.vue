<template>

  <div>
    <div class="hitcount" v-if="hitcount">Results: {{ hitcount }}</div>
    <ul class="results-list">
      <div v-if="endpoint == 'cases'">
        <case-result v-for="result in results[page]" :result="result" :key="result.id"></case-result>
      </div>
      <div v-if="endpoint == 'courts'" >
        <court-result v-for="result in results[page]" :result="result" :key="result.id"></court-result>
      </div>
      <div v-if="endpoint == 'jurisdictions'" >
        <jurisdiction-result v-for="result in results[page]" :result="result" :key="result.id"></jurisdiction-result>
      </div>
      <div v-if="endpoint == 'reporters'" >
        <reporter-result v-for="result in results[page]" :result="result" :key="result.id"></reporter-result>
      </div>
    </ul>
    <div v-if="this.$parent.results.length != 0" class="row">
      <div class="col-6">
        <button class="btn btn-sm" v-if="first_page !== true" @click="$emit('prev-page')">&lt;&lt; Prev Page {{ page
          }}
        </button>
        <button class="btn btn-sm disabled" v-else disabled>&lt;&lt; Prev Page</button>
      </div>
      <div class="col-6 text-right">
        <button class="btn btn-sm" v-if="last_page !== true" @click="$emit('next-page')">Next Page {{ page + 2 }}&gt;&gt;</button>
        <button class="btn btn-sm disabled" v-else disabled>Next Page &gt;&gt;</button>
      </div>
    </div>
  </div>
</template>



<script>
    export default {
        props: [
            'results',
            'endpoint',
            'hitcount',
            'page',
            'first_page',
            'last_page'
        ],
        methods: {
            case_view_url: function (case_id) {
                return case_view_url_template.replace('987654321', case_id)
            },
            metadata_view_url: function (endpoint, id) {
                return case_view_url_template.replace('987654321', id).replace('/case/', "/" + endpoint + "/")
            }

        }
    }
</script>