<template>
  <div id="categories-modal" tabindex="-1" role="dialog">
    <div class="categories-modal-dialog">
      <div class="modal-content">
        <div class="modal-header">
          <h5 class="modal-title">CATEGORIES</h5>
          <button type="button"
                  @click.stop="closeModal"
                  class="close"
                  data-dismiss="modal"
                  aria-label="Close">
            <span aria-hidden="true">&times;</span>
          </button>
        </div>
        <div class="modal-body">
          <span id="shape-label">Shape</span>
          <span id="input-label">Category Name</span>
          <span id="color-label">Color</span>
          <ul v-for="(cat, index) in categoryList" v-bind:key="index">
            <category :content="cat"></category>
          </ul>
          <div class="btn-group">
            <button class="btn btn-primary" @click="addCategoryFields">Add category
              <add-icon></add-icon>
            </button>
            <button class="btn btn-primary" @click="saveCategories">Save</button>
          </div>
          <div v-if="errors.length" class="form-errors p-2 mt-2 small">
            <b>Please correct the following error(s):</b>
            <ul class="m-0 list-inline">
              <li class="list-inline-item" v-for="error in errors" v-bind:key="error">{{ error }}</li>
            </ul>
          </div>

        </div>
      </div>
    </div>
  </div>

</template>

<script>
//eslint-disable-next-line
import Category from './category.vue'
import AddIcon from '../../../../static/img/icons/plus-circle.svg';
import store from "./store";

export default {
  name: "categories",
  components: {
    //eslint-disable-next-line
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
  methods: {
    checkForm() {
      this.errors = [];
      let uniqueCategories = new Set()
      for (let i = 0; i < this.categoryList.length; i++) {
        uniqueCategories.add(this.categoryList[i].name)
        console.log('adding', this.categoryList[i].name)
      }
      if (uniqueCategories.size !== this.categoryList.length) {
        this.errors.push('Categories must be unique.')
      }
      console.log(uniqueCategories, this.categoryList)
    },
    addCategoryFields() {
      this.categoryList.push(this.unbind(this.categoryTemplate))
    },
    unbind(obj) {
      return JSON.parse(JSON.stringify(obj))
    },
    closeModal() {
      this.$parent.closeModal();
    },
    saveCategories() {
      this.checkForm();
      if (this.errors.length) return;
      store.commit('addCategories', this.categoryList)
    }
  },
  mounted() {
    this.categoryList = store.getters.categories
    if (!this.categoryList.length) {
      this.addCategoryFields()
    }
  }
}
</script>
