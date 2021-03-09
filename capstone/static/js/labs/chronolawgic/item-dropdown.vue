<template>
  <div class="dropdown dropdown-field form-label-group">
    <button class="btn dropdown-toggle dropdown-title"
            type="button"
            :id="field.name"
            :ref="field.name"
            data-toggle="dropdown"
            aria-haspopup="true"
            aria-expanded="false"
            @click="toggleDropdown()"
            :aria-describedby="field.label">
      <span class="dropdown-title-text color-square" v-if="choices_type==='colors'"
             v-bind:style="{ background: display}"> {{ display }}
      </span>
      <span v-else class="dropdown-title-text">{{ display }}</span>
    </button>

    <!-- Choice fields -->
    <div class="dropdown-menu" ref="menu" v-bind:style="{
      'display': expanded ? 'block' : 'none'}"
         :aria-labelledby="field.name">
      <button v-for="choice in choices"
              v-bind:key="choice[0]"
              @click.stop="updateDropdownVal(choice, 'keyup')"
              :class="['dropdown-item', field.name===choice[0] ? 'active' : '']">
        <span @click.stop v-if="choices_type === 'color'" class="color-square"
              :style="'background-color:' + color[1] "></span>{{ choice[1] }}
      </button>
    </div>
    <button class="dropdown-item reset-field"
            v-if="original_display_val !== field.label && !(this.hide_reset)"
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
    'choices_type',
    'original_display_val'
  ],
  data() {
    return {
      hide_reset: true,
      display: this.original_display_val,
      expanded: false
    }
  },
  watch: {
    field: {
      handler: function (newval) {
        // this function is called if autofill with case (from search results) is triggered
        this.field.value = newval.value;
        this.display = newval.value;
      },
      deep: true
    }
  },
  methods: {
    dropdownReset() {
      this.original_display_val = this.field.label;
      this.field.value = "";
    },
    getFormattedDisplayValue() {
      // do nothing for regular text fields
      if (!this.choices) {
        return ''
      }
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
      this.field.value = choice[1];
      this.display = this.getFormattedDisplayValue();
      this.toggleDropdown()
    },
    toggleDropdown() {
      this.expanded = !this.expanded
    }
  },

}
</script>

<style scoped>

</style>