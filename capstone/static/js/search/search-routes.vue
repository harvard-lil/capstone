<template>
  <div class="row">
    <div class="col-12">
      <div class="dropdown dropdown-search-routes">
        <span class="fancy-for">for</span>
        <a class="btn btn-secondary dropdown-toggle dropdown-title"
           href="#"
           role="button"
           id="dropdownMenuLink"
           data-toggle="dropdown"
           aria-haspopup="true"
           aria-expanded="false">
          {{endpoint}}
        </a>

        <div class="dropdown-menu"
             data-toggle="dropdown" aria-haspopup="true" aria-expanded="false"
             aria-labelledby="dropdownMenuLink">
          <ul>
            <li class="search-tab"
                v-bind:key="current_endpoint"
                v-for="current_endpoint in endpoints">
              <a v-if="current_endpoint===endpoint"
                 @click="changeEndpoint(current_endpoint)"
                 href="#"
                 class="dropdown-item active">{{current_endpoint}}</a>
              <a v-else href="#"
                 @click="changeEndpoint(current_endpoint)"
                 class="dropdown-item">
                {{current_endpoint}}</a>
            </li>
          </ul>
        </div>
      </div>
    </div>
    <div class="endpoint-dropdown dropdown-menu"
         aria-labelledby="dropdownMenuButton">
      <ul>
        <li class="search-tab"
            v-for="current_endpoint in endpoints"
            v-bind:key="current_endpoint">
          <a v-if="current_endpoint===endpoint"
             @click="changeEndpoint(current_endpoint)"
             class="nav-link active">{{ current_endpoint }}</a>
          <a v-else
             @click="changeEndpoint(current_endpoint)"
             class="nav-link">
            {{current_endpoint }}</a>
        </li>
      </ul>
    </div>
  </div>
</template>

<script>
  export default {
    name: "searchroutes",
    props: ["endpoint"],
    data: function () {
      return {
        endpoints: Object.keys(this.$parent.endpoints),
        fields: [{
          name: "search",
          value: "",
          label: "Full-Text Search",
          default: true,
          format: "e.g. 'insurance' illinois",
          info: ""
        }], // just the default
      }
    },
    methods: {
      changeEndpoint: function (new_endpoint, fields=[]) {
        this.$parent.endpoint = new_endpoint;
        this.$parent.fields = fields;
      },
    }
  }
</script>
