<template>
  <div v-if="field['choices']">
    <div class="dropdown dropdown-field form-label-group"
         :class="{'querylabel_highlighted': field.highlight_explainer || field.highlight_field}">
      <button class="btn dropdown-toggle dropdown-title"
              type="button"
              :id="field.name"
              data-toggle="dropdown"
              aria-haspopup="true"
              aria-expanded="false"
              :aria-describedby="field.label"
              :class="[{'is-invalid': $store.getters.fieldHasError(field.name)},
                { 'queryfield_highlighted': field.highlight_explainer || field.highlight_field}]"
              @focus="$store.commit('highlightExplainer', field.name)"
              @blur="$store.commit('unhighlightExplainer', field.name)">
        <span class="dropdown-title-text">{{ display_value }}</span>
      </button>

      <!-- Choice fields -->
      <div class="dropdown-menu" :aria-labelledby="field.name">
        <button v-for="choice in field.choices"
                v-bind:key="choice[0]"
                @click.prevent="updateDropdownVal(choice)"
                :class="['dropdown-item', 'search-tab', field.name===choice[0] ? 'active' : '']">
          {{ choice[1] }}
        </button>
      </div>
    </div>
    <button class="dropdown-item reset-field"
            v-if="display_value !== field.label && !(this.field.label === 'sort_field')"
            @click="$store.commit('clearField', field.name)">
      <small>Reset {{ field.label }} field</small></button>

  </div>
  <!-- for text, numbers, and everything else (that we presume is text) -->
  <div v-else class="form-label-group">
    <input v-model='value'
           :aria-label="field.name"
           :class="['queryfield', 'col-12',
           {'is-invalid': $store.getters.fieldHasError(field.name)},
           { 'queryfield_highlighted': field.highlight_explainer || field.highlight_field} ]"
           :type='field.type'
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


export default {
  name: "field-item",
  props: [ 'field' ],
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
      })
      if (matched_pair[0]) {
        return this.field.label + ': ' + matched_pair[0][1]
      } else {
        return this.field.label
      }
    },

    updateDropdownVal(choice) {
      this.field.value = choice[0];
      if (this.field.name !== 'ordering') {
        this.display_value = this.getFormattedDisplayValue();
      } else {
        this.$parent.updateOrdering();
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
      }
    }
  },

}
</script>
