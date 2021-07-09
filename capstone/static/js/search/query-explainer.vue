<template>
  <a id="query-explainer" class="text-break" :href="$store.getters.new_query_url">
    <span>{{ $store.getters.api_root }}</span>
    <template v-for="(field, name) in $store.getters.fields">
      <span :key="'explainer_' + name"
          v-if="field.value && field.value.length"
          :data-field-name="name"
          :class="{'highlight-parameter': field.highlight_explainer || field.highlight_field}"
          v-on:mouseenter="$store.commit('highlightField', name)"
          v-on:mouseleave="$store.commit('unhighlightField', name)"
          class="api_url_segment">
        <template v-if="Array.isArray(field.value)">
          <span v-for="field_instance_value in field.value"
                v-text="name + '=' + field_instance_value"
                class="api_url_instance_segment"
                :key="'explainer_multiple_value_instance' + field_instance_value">
          </span>
        </template>
        <template v-else>
          <span v-text="name + '=' + field.value"></span>
        </template>
      </span>
    </template>
  </a>
</template>

<script>
  export default {
  }
</script>
