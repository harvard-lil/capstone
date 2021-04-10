<template>
  <li class="category">
    <v-select :options="shapes"
              transition=""
              class="shape-select"
              v-model="content.shape"
              :filterable="false"
              :clearable="false"
              label="shape">
      <template #selected-option="{ shape }">
        <shape-component :width="28" :color="content.color" :shapetype="shape"></shape-component>
      </template>

      <template #option="{ shape }">
        <shape-component :width="28" :color="content.color" :shapetype="shape"></shape-component>
      </template>
    </v-select>
    <input v-model="content.name" class="shape-name" required>
    <v-select transition=""
              :filterable="false"
              :clearable="false"
              class="color-dropdown shape-color"
              label="color"
              v-model="content.color"
              :options="colors">
      <template #selected-option="{ color }">
        <span :style="{backgroundColor: color}"
              class="color-square">
        </span>
      </template>
      <template #option="{ color }">
        <span :style="{backgroundColor: color}"
              class="color-square">
        </span>
      </template>
    </v-select>
    <button type="button" @click="$parent.removeCategory(content.id)" class="close category-remove" data-dismiss="modal" aria-label="Close">
      <span aria-hidden="true">&times;</span>
    </button>
  </li>
</template>

<script>
import vSelect from 'vue-select'

import ShapeComponent from './shape-component.vue';
import store from "./store";

export default {
  name: "category",
  props: ['content'],
  components: {
    vSelect,
    ShapeComponent,
  },
  data() {
    return {
      shapes: ['circle', 'polygon1', 'polygon2', 'rhombus', 'triangle'],
      colors: [],
    }
  },
  methods: {
    getRandom(someList) {
      return someList[Math.floor(Math.random() * someList.length)]
    },
  },

  mounted() {
    this.colors = store.getters.choices.colors;
    if (!this.content.shape)
      this.content.shape = this.getRandom(this.shapes);
    if (!this.content.color)
      this.content.color = this.getRandom(this.colors);
  },
}
</script>

<style scoped>

</style>