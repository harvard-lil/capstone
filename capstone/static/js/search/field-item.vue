<template>
  <div v-if="field['choices']" class="form-label-group">
      <v-select multiple :options="choices"
        @focus="$store.commit('highlightExplainer', field.name)"
        @blur="$store.commit('unhighlightExplainer', field.name)"
        v-model="value"
        :aria-label="field.name"
        :placeholder="field.label"
        label="label"
        :clearable="clearable"
        value="value"
        :id="field.name"
        :reduce="option => option.value"
        :class="['dropdown-field', 'col-12',
           {'is-invalid': $store.getters.fieldHasError(field.name)},
           { 'queryfield_highlighted': field.highlight_field} ]">
        <template #selected-option-container="{ option }">
          <div class="vs__selected">{{ option.label }}</div>
        </template>
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
  props: [ 'field', 'search_on_change', 'clearable' ],
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
    choices: function () {
      return this.field['choices'].map((element) => { return  {'label': element[1], 'value': element[0] } })
    }
  },

}
</script>

