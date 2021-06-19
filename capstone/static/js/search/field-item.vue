<template>
  <div v-if="field['choices']" class="form-label-group">
      <v-select :options="field['choices']"
        @focus="$store.commit('highlightExplainer', field.name)"
        @blur="$store.commit('unhighlightExplainer', field.name)"
        v-model="value"
        :multiple="multiple"
        :aria-label="field.name"
        :placeholder="field.label"
        :clearable="clearable"
        :id="field.name"
        :reduce="option => option.value"
        :class="['dropdown-field', 'col-12',
           {'is-invalid': $store.getters.fieldHasError(field.name)},
           { 'queryfield_highlighted': field.highlight_field} ]">

      </v-select>
  </div>
  <!-- for text, numbers, and everything else (that we presume is text) -->
  <div v-else class="form-label-group">
    <input v-model='value'
           :aria-label="field.name"
           :class="['queryfield', 'col-12',
           {'is-invalid': $store.getters.fieldHasError(field.name)},
           { 'queryfield_highlighted': field.highlight_field} ]"
           type='text'
           :placeholder="field.label"
           :id="field.name"
           :min="field.min"
           :max="field.max"
           @focus="$store.commit('highlightExplainer', field.name)"
           @blur="$store.commit('unhighlightExplainer', field.name)"
           v-on:keyup.enter="$store.dispatch('searchFromForm')">
    <label :for="field.name">
      {{ field.label }}
    </label>
  </div>
</template>

<script>
import vSelect from 'vue-select';

export default {
  components: {vSelect},
  name: "field-item",
  props: [ 'field', 'search_on_change', 'clearable', 'multiple' ],
  computed: {
    value: {
      get () {
        return this.field.value
      },
      set (value) {
        this.$store.commit('setFieldValue', {'name': this.field.name, 'value': value })
        if (this.search_on_change) {
          this.$store.dispatch('searchFromForm');
        }
      }
    },
  },

}
</script>

