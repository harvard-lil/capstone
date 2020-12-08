<template>
  <div v-if="field['choices']" class="dropdown dropdown-field">
    <button class="btn dropdown-toggle dropdown-title"
            type="button"
            :id="field.name"
            data-toggle="dropdown"
            aria-haspopup="true"
            aria-expanded="false"
            :aria-describedby="field.label"
            @focus="highlightExplainer"
            @blur="unhighlightExplainer">
      {{ field.display_value ? field.display_value : field.label }}
    </button>

    <div class="dropdown-menu" :aria-labelledby="field.name">
      <!-- Include reset field -->
      <a class="dropdown-item reset-field"
         v-if="field.display_value"
         @click="updateDropdownVal(index, ['', ''])">
        Reset field</a>
      <!-- Choice fields -->
      <a v-for="choice in $parent.choices[field['choices']]" v-bind:key="choice[0]"
         @click="updateDropdownVal(index, choice)"
         :class="['dropdown-item', 'search-tab', field.name===choice[0] ? 'active' : '']">
        {{ choice[1] }}
      </a>
    </div>
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
  methods: {
    updateDropdownVal(index, choice) {
      this.$parent.fields[index].value = choice[0];
      this.$parent.fields[index].display_value = choice[1];
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