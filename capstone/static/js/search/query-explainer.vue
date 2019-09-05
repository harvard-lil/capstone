<template>
    <code>
      <a id="query-explainer" :href="query_url">
        <span>{{ base_url }}</span>
        <span v-for="(argument, index) in url_arguments"
              :key="index" class="api_url_segment"
              v-on:mouseenter="highlightQuery"
              v-on:mouseleave="unhighlightQuery"
              @focus.native="alert('asd')"
              :id="argumentID(argument)">
          <template v-if="index === 0">?</template><template v-else>&</template>{{argument}}</span>
      </a>
    </code>
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
      query_url: function() {
          this.update_string(this.query_url);
      }
    },
    methods: {
      update_string(url){
        var split_url = url.split("?");
        this.url_arguments = split_url[1].split("&");
        this.base_url = split_url[0];
      },
      highlightQuery(event){
        var box_element = this.getInputBoxFromParameter(event.target.textContent);

        if (box_element && !box_element.classList.contains("queryfield_highlighted")) {
            var label = box_element.parentElement.parentElement.getElementsByClassName('querylabel')[0];
            box_element.classList.add("queryfield_highlighted")
            label.classList.add("querylabel_highlighted")
        }
      },
      unhighlightQuery(event){
        var box_element = this.getInputBoxFromParameter(event.target.textContent);
        if (box_element && box_element.classList.contains("queryfield_highlighted")) {
            var label = box_element.parentElement.parentElement.getElementsByClassName('querylabel')[0];
            box_element.classList.remove("queryfield_highlighted")
            label.classList.remove("querylabel_highlighted")
        }
      },
      getInputBoxFromParameter(parameter) {
        var target_id = parameter.substring(1, parameter.indexOf('='));
        return document.getElementById(target_id);
      },
      argumentID(parameter) {
        return "p_" + parameter.substring(0, parameter.indexOf('='));
      }
    }
  }
</script>