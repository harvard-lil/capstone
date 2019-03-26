<template>
  <li class="result">
    <div class="result-title row">
      <div class="col-md-9">

        <a target="_blank" class="simple"
          :href="$parent.metadata_view_url('court', result.id)" v-text="result.name">
        </a>
      </div>
      <div class="col-md-3 decision-date">
          <a class="see-cases"
             @click="$parent.$emit('see-cases', 'court', result.slug)">
            See cases
          </a>
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