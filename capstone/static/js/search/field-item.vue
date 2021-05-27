<template>
  <div v-if="field['choices']" class="form-label-group">
      <v-select :options="choices"
        @focus="$store.commit('highlightExplainer', field.name)"
        @blur="$store.commit('unhighlightExplainer', field.name)"
        v-model="value"
        :aria-label="field.name"
        :clearable="true"
        :placeholder="field.label"
        label="label"
        :searchable="false"
        value="value"
        :id="field.name"
        :reduce="option => option.value"
        :class="['dropdown-field', 'col-12',
           {'is-invalid': $store.getters.fieldHasError(field.name)},
           { 'queryfield_highlighted': field.highlight_explainer || field.highlight_field} ]">
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
           { 'queryfield_highlighted': field.highlight_explainer || field.highlight_field} ]"
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
  props: [ 'field', 'search_on_change' ],
  data() {
    return {
      display_value: this.getFormattedDisplayValue()
    }
  },
  methods: {
    getFormattedDisplayValue() {
     // do nothing for regular text fields
      if (!this.field.choices) {
        return ''
      }
      // for dropdown fields, if field value is set in parameter, display that along with field label
      let matched_pair = this.field.choices.filter((choice_pair) => {
        return this.field.value === choice_pair[0]
      });
      if (matched_pair[0]) {
        return this.field.label + ': ' + matched_pair[0][1]
      } else {
        return this.field.label
      }
    },
  },
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

