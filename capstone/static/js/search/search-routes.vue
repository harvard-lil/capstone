<template>
  <div class="row">
    <div class="col-1 fancy-for">
      for
    </div>
    <div class="col-11">
      <div class="dropdown dropdown-search-routes">
        <button class="btn dropdown-toggle dropdown-title"
           type="button"
           id="search-routes-dropdown"
           data-toggle="dropdown"
           aria-haspopup="true"
           aria-expanded="false">
          {{endpoint}}
        </button>

        <div class="dropdown-menu" aria-labelledby="search-routes-dropdown">
          <button type="button"
                  v-for="current_endpoint in endpoints" :key="current_endpoint"
                  @click="changeEndpoint(current_endpoint)"
                  :class="['dropdown-item', 'search-tab', current_endpoint===endpoint ? 'active' : '']">
            {{current_endpoint}}
          </button>
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
      changeEndpoint: function (new_endpoint, fields = []) {
        this.$parent.endpoint = new_endpoint;
        this.$parent.fields = fields;
      },
    }
  }
</script>
