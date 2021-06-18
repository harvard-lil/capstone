<template>
  <div class="sidebar" id="timeline-meta">
    <div class="sidebar-content">
      <minimap></minimap>
    </div>

  </div>
</template>

<script>
import Minimap from './minimap';

export default {
  name: "Sidebar",
  components: {
    Minimap
  },

}
</script>

<style scoped>

</style>