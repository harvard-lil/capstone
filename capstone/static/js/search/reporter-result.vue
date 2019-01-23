<template>
  <li class="result">
    <div class="result-title row">
      <a target="_blank" :href="$parent.metadata_view_url('reporter', result.id)">
        {{result.full_name}}
      </a>
    </div>
    <div class="result-data">
      <div class="row">
        <div>
          <span class="result-data-label">Abbreviation:</span> {{ result.short_name }}
        </div>
        <div>
          <a href="#"
             class="see-cases"
             @click="$parent.$emit('see-cases', 'reporter', result.id)">
            See cases
          </a>
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