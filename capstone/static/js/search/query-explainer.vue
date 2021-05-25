<template>
  <a id="query-explainer" class="text-break" :href="$store.getters.new_query_url">
    <span>{{ $store.getters.api_root }}</span>
    <span v-for="(field, name) in $store.getters.fields" :key="'explainer_' + name" v-show="field.value"
          v-text="name + '=' + field.value"
          class="api_url_segment"
          :data-field-name="name"
          :class="{'highlight-parameter': field.highlight_explainer || field.highlight_field}"
          v-on:mouseenter="$store.commit('highlightField', name)"
          v-on:mouseleave="$store.commit('unhighlightField', name)">
    </span>
  </a>
</template>

<script>
  export default {
  }
</script>

<style>

  .api_url_segment {
    padding-left: .2rem;
    padding-right: .2rem;
  }
  .text-break > .api_url_segment:before {
    content: '?';
  }
  .text-break > .api_url_segment ~ .api_url_segment:before {
    content: '&';
  }

</style>