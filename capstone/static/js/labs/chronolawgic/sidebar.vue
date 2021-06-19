<template>
  <div class="sidebar" id="timeline-meta">
    <div class="sidebar-content">
      <div class="small font-italic text-center">
        <router-link to="/">
          <arrow-left-circle/>
        </router-link>
        Built using Chronolawgic: a legal timeline tool
      </div>
      <minimap></minimap>
      <div class='h2o-error-container' v-if="this.$store.getters.missingCases.length">
        <b>Please be sure to double-check the imported cases for <accuracy class=""></accuracy></b><br/>
        <b>We couldn't find some cases. This can happen if the citation is wrong or is outside of the bounds of CAP data.</b>
        <br/>
          You may need to add these by hand:
        <br/><br/>
        <ul>
          <li v-for="(c, idx) in this.$store.getters.missingCases" v-bind:key="idx">
            <a :href="'https://opencasebook.org' + c.original_url"><b>{{ c.name }}</b></a>&nbsp;
            <i>{{ c.citations[0] }}</i>
          </li>
        </ul>
      </div>
    </div>
  </div>
</template>
<script>
import Minimap from './minimap';
import ArrowLeftCircle from '../../../../static/img/icons/arrow-left-circle.svg';

export default {
  name: "Sidebar",
  components: {
    Minimap,
    ArrowLeftCircle,
  },
}
</script>
