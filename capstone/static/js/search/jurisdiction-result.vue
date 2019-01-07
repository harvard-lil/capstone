<template>
  <li class="result">
    <div class="result-title row">
      <div class="row">
        <div class="result-title col-12">
          <a target="_blank" v-text="result.name_long" :href="$parent.metadata_view_url('jurisdiction', result.id)"></a>
        </div>
      </div>
    </div>
    <div class="result-data">
      <div class="row">
        <div class="col-6">
          <span class="result-data-label">Abbreviation:</span> {{ result.name }}
        </div>
        <div class="col-4">
          <span class="result-data-label">Slug:</span> {{ result.slug }}
        </div>
        <div class="col-2 text-right">
          <button @click="$parent.$emit('see-cases', 'jurisdiction', result.slug)">Cases</button>
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