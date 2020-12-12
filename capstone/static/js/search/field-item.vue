<template>
  <div v-if="field['choices']">
    <div class="dropdown dropdown-field">
      <button class="btn dropdown-toggle dropdown-title"
              type="button"
              :id="field.name"
              data-toggle="dropdown"
              aria-haspopup="true"
              aria-expanded="false"
              :aria-describedby="field.label"
              @focus="highlightExplainer"
              @blur="unhighlightExplainer">
        {{ display_value }}
      </button>


      <div class="dropdown-menu" :aria-labelledby="field.name">
        <!-- Choice fields -->
        <a v-for="choice in $parent.choices[field['choices']]" v-bind:key="choice[0]"
           @click="updateDropdownVal(index, choice)"
           :class="['dropdown-item', 'search-tab', field.name===choice[0] ? 'active' : '']">
          {{ choice[1] }}
        </a>
      </div>
    </div>
    <a class="dropdown-item reset-field"
       v-if="display_value !== field.label"
       href="#"
       @click.prevent="dropdownReset()">
      <small>Reset {{ field.label }} field</small></a>

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
    <label :for="field.name">{{ field.label }}</label>

  </div>
</template>

<script>
export default {
  name: "field-item",
  props: [
    'field',
    'index'
  ],
  data() {
    return {
      display_value: this.field.label
    }
  },
  methods: {
    dropdownReset() {
      this.display_value = this.field.label;
      this.field.value = "";
    },
    updateDropdownVal(index, choice) {
      this.field.value = choice[0];
      this.display_value = choice[1];
      this.$parent.valueUpdated()
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
  }
}
</script>

<style scoped>

</style>