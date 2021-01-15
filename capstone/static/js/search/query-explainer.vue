<template>
  <a id="query-explainer" class="text-break" :href="query_url">
    <span>{{ base_url }}</span>
    <span v-for="(argument, index) in url_arguments"
          :key="index" class="api_url_segment"
          v-on:mouseenter="highlightQuery"
          v-on:mouseleave="unhighlightQuery"
          @focus.native="alert('asd')"
          :id="argumentID(argument)">
          <template v-if="index === 0">?</template><template v-else>&</template>{{ argument }}</span>
  </a>
</template>

<script>
  export default {
    props: [
      'query_url'
    ],
    data: function () {
      return {
        url_arguments: [],
        base_url: ''
      }
    },
    watch: {
      query_url: function () {
        this.update_string(this.query_url);
      }
    },
    methods: {
      update_string(url) {
        let split_url = url.split("?");
        this.url_arguments = split_url[1].split("&");
        this.base_url = split_url[0];
      },
      highlightQuery(event) {
        let box_element = this.getInputBoxFromParameter(event.target.textContent);

        if (box_element && !box_element.classList.contains("queryfield_highlighted")) {
          let itemToHighlight = box_element.parentElement;
          box_element.classList.add("queryfield_highlighted")
          itemToHighlight.classList.add("querylabel_highlighted")
        }
      },
      unhighlightQuery(event) {
        let box_element = this.getInputBoxFromParameter(event.target.textContent);
        if (box_element && box_element.classList.contains("queryfield_highlighted")) {
          let itemToHighlight = box_element.parentElement;
          box_element.classList.remove("queryfield_highlighted")
          itemToHighlight.classList.remove("querylabel_highlighted")
        }
      },
      getInputBoxFromParameter(parameter) {
        let target_id = parameter.substring(1, parameter.indexOf('='));
        return document.getElementById(target_id);
      },
      argumentID(parameter) {
        return "p_" + parameter.substring(0, parameter.indexOf('='));
      }
    }
  }
</script>