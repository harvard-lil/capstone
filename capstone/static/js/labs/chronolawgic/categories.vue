<template>
  <div id="categories-modal" tabindex="-1" role="dialog">
    <div class="categories-modal-dialog">
      <div class="modal-content">
        <div class="modal-header">
          <h5 class="modal-title">CATEGORIES</h5>
          <button type="button"
                  @click.stop="$parent.toggleKey()"
                  class="close"
                  data-dismiss="modal"
                  aria-label="Close">
            <span aria-hidden="true">&times;</span>
          </button>
        </div>
        <div class="modal-body" v-if="this.$store.state.isAuthor">
          <ul>
            <li class="category">
              <span id="shape-label">Shape</span>
              <span id="input-label">Name</span>
              <span id="color-label">Color</span>
              <span></span>
            </li>
            <category v-for="(cat, index) in categoryList" v-bind:key="index" :content="cat"></category>
          </ul>
          <div class="btn-group">
            <button class="btn btn-tertiary" @click="addCategoryFields">New
              <add-icon></add-icon>
            </button>
            <button class="btn btn-tertiary" @click="$parent.toggleKey">Cancel</button>
            <button class="btn btn-primary" @click="saveCategories">Save</button>
          </div>
          <div v-if="errors.length" class="form-errors p-2 mt-2 small">
            <b>Please correct the following error(s):</b>
            <ul class="m-0 list-inline">
              <li class="list-inline-item" v-for="error in errors" v-bind:key="error">{{ error }}</li>
            </ul>
          </div>
        </div>
        <div class="modal-body" v-else>
          <ul>
            <li class="category-readonly" v-for="(cat, index) in categoryList" v-bind:key="index">
              <span><shape-component :width="28" :color="cat.color" :shapetype="cat.shape"></shape-component></span>
              <span class="name" v-text="cat.name"></span>
            </li>
          </ul>
        </div>
      </div>
    </div>
  </div>

</template>

<script>
import Category from './category.vue'
import AddIcon from '../../../../static/img/icons/plus-circle.svg';
import store from "./store";
import {EventBus} from "./event-bus.js";
import ShapeComponent from "./shape-component.vue";

export default {
  name: "categories",
  components: {
    ShapeComponent,
    Category,
    AddIcon
  },

  data() {
    return {
      errors: [],
      vectors: [],
      colors: [],
      categoryList: [],
      categoryTemplate: {
        shape: '',
        name: '',
        color: ''
      }
    }
  },
  watch: {
    categoryList: {

      handler(newval) {
        this.categoryList = newval;
      },
      deep: true
    }
  },
  methods: {
    checkForm() {
      this.errors = [];
      let uniqueCategories = new Set()
      for (let i = 0; i < this.categoryList.length; i++) {
        uniqueCategories.add(this.categoryList[i].name)
      }
      if (uniqueCategories.size !== this.categoryList.length) {
        this.errors.push('Categories must be unique.')
      }
    },
    addCategoryFields() {
      this.categoryList.push(this.unbind(store.getters.templateCategory))
    },
    unbind(obj) {
      return JSON.parse(JSON.stringify(obj))
    },
    saveCategories() {
      this.checkForm();
      if (this.errors.length) return;
      EventBus.$emit('updateCategories', this.categoryList);
      store.commit('updateCategories', this.categoryList);
      // close "modal"
      this.$parent.toggleKey();
    },
    removeCategory(catID) {
      let catIndex = -1;
      for (let i = 0; i < this.categoryList.length; i++) {
        if (this.categoryList[i].id === catID) {
          catIndex = i;
          break;
        }
      }
      if (catIndex > -1) {
        this.categoryList.splice(catIndex, 1)
      }
    }
  },
  mounted() {
    this.categoryList = this.unbind(store.getters.categories)
    if (!this.categoryList.length) {
      this.addCategoryFields()
    }
  }
}
</script>
