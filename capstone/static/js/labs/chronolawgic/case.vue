<template>
  <button class="case-button"
          type="button"
          @focus="handleFocus"
          @click="openModal(case_data)"
          data-toggle="modal"
          :data-target="dataTarget"
          tabindex="0">
    <article class="case">
      <div :style="{backgroundColor: case_data.color}"
           class="border">
      </div>
      <header>
        <!--this is just for name placement if we don't have categories-->
        <span class="case-name">
            {{ case_data.name }}
        </span>
        <a class="case-link" v-if="case_data.url"
           :href="case_data.url" target="_blank" @click.stop>
          <link-case/>
        </a>
      </header>
      <section class="desc">
        {{ case_data.short_description }}
      </section>
      <div class="categories"
           v-if="categories && categories.length">
        <ul class="list-inline">
          <li class="list-inline-item"
              v-for="category in categories"
              title="category.name"
              v-bind:key="category.id">
            <shape-component :width="20"
                             :title="category.name"
                             :color="category.color"
                             :shapetype="category.shape">
            </shape-component>
          </li>
        </ul>
      </div>
    </article>
  </button>
</template>

<script>
import LinkCase from '../../../../static/img/icons/open_in_new-24px.svg';
import {EventBus} from "./event-bus.js";
import store from "./store";
import ShapeComponent from './shape-component';

export default {
  name: "Case",
  props: ['case_data', 'year_value'],
  components: {LinkCase, ShapeComponent},
  computed: {
    dataTarget: () => {
      if (store.getters.isMobile || !store.state.isAuthor) {
        return '#readonly-modal'
      } else {
        return '#add-case-modal'
      }
    },
  },
  watch: {
    case_data: {
      handler(newval) {
        this.case_data.categories = newval.categories;
        this.hydrateCategories();
      },
      deep: true
    }
  },
  data() {
    return {
      categories: [],
      timelineCategories: store.getters.categories
    }
  },
  methods: {
    openModal(item) {
      this.$parent.$parent.openModal(item, 'case')
    },
    closeModal() {
      EventBus.$emit('closeModal')
    },
    handleFocus() {
      EventBus.$emit('closePreview')
    },
    repopulateTimeline() {
      this.$parent.repopulateTimeline();
    },
    hydrateCategories() {
      this.categories = [];
      for (let i = 0; i < this.case_data.categories.length; i++) {
        let foundCat = this.timelineCategories.find(cat => cat.id === this.case_data.categories[i])
        if (foundCat) {
          this.categories.push(foundCat)
        }
      }
    }
  },
  mounted() {
    if (this.case_data.categories) {
      this.hydrateCategories();
    }
    EventBus.$on('updateCategories', (categories) => {
      if (!this.case_data.categories)
        return;
      this.timelineCategories = categories;
      this.hydrateCategories();
    });
  }
}
</script>

