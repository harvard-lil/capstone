<template>
  <li class="result">
    <div class="result-title row">
      <div class="row">
        <div class="result-title col-12">
          <a target="_blank" v-text="result.name_abbreviation"
             :href="$parent.metadata_view_url('court', result.id)"></a>
        </div>
      </div>
    </div>
    <div class="result-data">
      <div class="row">
        <div class="col-6">
          <span class="result-data-label">Abbreviation:</span> {{ result.name_abbreviation }}
        </div>
        <div class="col-3">
          <span class="result-data-label">Jurisdiction:</span> {{ result.jurisdiction }}
        </div>
        <div class="col-3 text-right">
          <button @click="$parent.$emit('see-cases', 'court', result.slug)">Cases</button>
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