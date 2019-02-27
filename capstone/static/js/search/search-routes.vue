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
                  v-for="current_endpoint in Object.keys(endpoints)" :key="current_endpoint"
                  @click="changeEndpoint(current_endpoint)"
                  :class="['dropdown-item', 'search-tab', current_endpoint===endpoint ? 'active' : '']">
            {{current_endpoint}}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
  export default {
    name: "searchroutes",
    props: ["endpoint", "endpoints"],
    methods: {
      changeEndpoint: function (new_endpoint) {
        this.$router.push({ name: 'endpoint', params: { endpoint: new_endpoint } });
      },
    }
  }
</script>
