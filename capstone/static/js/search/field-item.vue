<template>
  <div :ref='"field_" + field.name' v-if="field['choices']">
    <div class="dropdown dropdown-field form-label-group">
      <button class="btn dropdown-toggle dropdown-title"
              type="button"
              :id="field.name"
              data-toggle="dropdown"
              aria-haspopup="true"
              aria-expanded="false"
              :aria-describedby="field.label"
              @focus="highlightExplainer"
              @blur="unhighlightExplainer">
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
  <textarea :ref='"field_" + field.name'  v-else-if="field.type === 'textarea'"
            :aria-label="field.name"
            v-model="value"
            :class="['queryfield', $store.getters.fieldHasError(field.name) ? 'is-invalid' : '', 'col-12' ]"
            :id='field["name"]'
            :placeholder='field["placeholder"] || false'
            class="form-control"
            @focus="highlightExplainer"
            @blur="unhighlightExplainer">
        </textarea>
  <!-- for text, numbers, and everything else (that we presume is text) -->
  <div :ref='"field_" + field.name' v-else class="form-label-group">
    <input v-model='value'
           :aria-label="field.name"
           :class="['queryfield', $store.getters.fieldHasError(field.name) ? 'is-invalid' : '', 'col-12' ]"
           :type='field.type'
           :placeholder="field.label"
           :id="field.name"
           :min="field.min"
           :max="field.max"
           @focus="highlightExplainer"
           @blur="unhighlightExplainer">
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

    highlightExplainer(event) {
      let explainer_argument = document.getElementById("p_" + event.target.id);
      if (explainer_argument) {
        explainer_argument.classList.add('highlight-parameter');
      }
    },
    unhighlightExplainer(event) {
      let explainer_argument = document.getElementById("p_" + event.target.id);
      if (explainer_argument) {
        explainer_argument.classList.remove('highlight-parameter');
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
