<template>
  <div class="sidebar" id="timeline-meta">
    <div class="sidebar-content">
      <div class="small font-italic text-center">
        <router-link to="/">
          <arrow-left-circle />
        </router-link>
        Built using Chronolawgic: a legal timeline tool</div>
      <div class="my-timelines-link" v-if="$store.state.isAuthor">

      </div>
      <minimap></minimap>
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
