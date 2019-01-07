<template>
  <li class="result">
    <div class="result-title row">
      <div class="row">
        <div class="result-title col-12">
          <a target="_blank" v-text="result.full_name" :href="$parent.metadata_view_url('reporter', result.id)"></a>
        </div>
      </div>
    </div>
    <div class="result-data">
      <div class="row">
        <div class="col-9">
          <span class="result-data-label">Abbreviation:</span> {{ result.short_name }}
        </div>
        <div class="col-3 text-right">
          <button @click="$parent.$emit('see-cases', 'reporter', result.id)">Cases</button>
        </div>
      </div>
    </div>
  </li>
</template>

<script>
    module.exports = {
        props: [
            'result'
        ],
    }
</script>