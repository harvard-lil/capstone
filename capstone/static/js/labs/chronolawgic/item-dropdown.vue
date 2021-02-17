<template>
  <div class="dropdown dropdown-field form-label-group">
    <button class="btn dropdown-toggle dropdown-title"
            type="button"
            :id="field.name"
            data-toggle="dropdown"
            aria-haspopup="true"
            aria-expanded="false"
            :aria-describedby="field.label">
      <span class="dropdown-title-text">{{ display_value }}</span>
    </button>

    <!-- Choice fields -->
    <div class="dropdown-menu" :aria-labelledby="field.name">
      <button v-for="choice in choices"
              v-bind:key="choice[0]"
              @click="updateDropdownVal(choice, 'keyup')"
              :class="['dropdown-item', field.name===choice[0] ? 'active' : '']">
        {{ choice[1] }}
      </button>
    </div>
    <button class="dropdown-item reset-field"
            v-if="display_value !== field.label && !(this.hide_reset)"
            @click.stop="dropdownReset()">
      <small>Reset {{ field.label }} field</small>
    </button>
  </div>

</template>

<script>

export default {
  name: "item-dropdown",
  props: [
    'field',
    'choices',
    'display_value'
  ],
  data() {
    return {
      hide_reset: true
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
        return matched_pair[0][1]
      } else {
        return this.field.label
      }
    },
    updateDropdownVal(choice) {
      this.field.value = choice[0];
      this.display_value = this.getFormattedDisplayValue();
    },
  }
}
</script>

<style scoped>

</style>