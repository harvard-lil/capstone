<template>
  <div v-if="field['choices']">
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
        <button v-for="choice in choices"
                v-bind:key="choice[0]"
                @click.prevent="updateDropdownVal(choice)"
                :class="['dropdown-item', 'search-tab', field.name===choice[0] ? 'active' : '']">
          {{ choice[1] }}
        </button>
      </div>
    </div>
    <button class="dropdown-item reset-field"
            v-if="display_value !== field.label && !(this.hide_reset)"
            @click="dropdownReset()">
      <small>Reset {{ field.label }} field</small></button>
  </div>
  <textarea v-else-if="field.type === 'textarea'"
            :aria-label="field.name"
            v-model="field.value"
            :class="['queryfield', $parent.field_errors[field.name] ? 'is-invalid' : '', 'col-12' ]"
            :id='field["name"]'
            :placeholder='field["placeholder"] || false'
            class="form-control"
            v-on:keyup="$parent.valueUpdated"
            @focus="highlightExplainer"
            @blur="unhighlightExplainer">
        </textarea>
  <!-- for text, numbers, and everything else (that we presume is text) -->
  <div v-else class="form-label-group">
    <input v-model='field.value'
           :aria-label="field.name"
           :class="['queryfield', $parent.field_errors[field.name] ? 'is-invalid' : '', 'col-12' ]"
           :type='field.type'
           :placeholder="field.label"
           :id="field.name"
           :min="field.min"
           :max="field.max"
           @input="$parent.valueUpdated"
           @focus="highlightExplainer"
           @blur="unhighlightExplainer">
    <label :for="field.name">
      {{ field.label }}
    </label>

  </div>
</template>

<script>
import {EventBus} from "./event-bus";


export default {
  name: "field-item",
  props: [
    'field',
    'hide_reset',
    'choices',
  ],
  data() {
    return {
      display_value: this.getFormattedDisplayValue()
    }
  },
  methods: {
    dropdownReset() {
      this.display_value = this.field.label;
      this.field.value = "";
    },
    getFormattedDisplayValue() {
      // do nothing for regular text fields
      if (!this.choices) {
        return ''
      }
      // for dropdown fields, if field value is set in parameter, display that along with field label
      let matched_pair = this.choices.filter((choice_pair) => {
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
  mounted() {
    EventBus.$on('resetField', (name) => {
      if (name === this.field.name) {
        this.dropdownReset()
      }
    })
  }
}
</script>
