<template>
  <div class="sidebar" id="timeline-meta">
    <div class="sidebar-content text-center">
      <div class="small font-italic">
        <router-link to="/">
          <arrow-left-circle/>
        </router-link>
        Built using Chronolawgic: a legal timeline tool
      </div>
      <minimap></minimap>
      <br/>
      <a class="btn btn-primary btn-download" @click="download()">Download timeline JSON
        <download-icon></download-icon>
      </a>
      <div class='h2o-error-container'
           v-if="this.$store.state.isAuthor && this.id === this.missingCases.id && this.missingCases.cases">
        <b>Please be sure to double-check the imported cases for accuracy.</b><br/>
        <b>We couldn't find some cases. This can happen if the citation is wrong or is outside of the bounds of CAP
          data.</b>
        <br/>
        You may need to add these by hand:
        <br/><br/>
        <ul>
          <li v-for="(c, idx) in this.missingCases.cases" v-bind:key="idx">
            <a :href="'https://opencasebook.org' + c.original_url"><b>{{ c.name }}</b></a>&nbsp;
            <i>{{ c.citations[0] }}</i>
          </li>
        </ul>
      </div>
      <div v-if="!this.$store.state.isAuthor" class="disclaimer mt-4 pl-2 pr-2">
        Note: timelines are user generated and are not reviewed by the Caselaw Access Project. <br/><a
          :href="this.$store.state.urls.chronolawgic">Create your
        own timeline! </a><br/><br/>
        To let us know about inappropriate content,
        <a :href="this.$store.state.urls.contact">click here</a>.
      </div>
    </div>
  </div>
</template>
<script>
import Minimap from './minimap.vue';
import ArrowLeftCircle from '../../../../static/img/icons/arrow-left-circle.svg';
import DownloadIcon from '../../../../static/img/icons/download.svg';

export default {
  name: "Sidebar",
  components: {
    Minimap,
    ArrowLeftCircle,
    DownloadIcon,
  },
  computed: {
    missingCases() {
      return this.$store.getters.missingCases;
    },
    id() {
      return this.$store.getters.id;
    }
  },
  watch: {
    missingCases() {
      this.$store.getters.missingCases;
    },
    id() {
      this.$store.getters.id;
    }
  },
  methods: {
    download() {
      // allow for json downloading
      // todo: include CSV option
      let timeline = this.$store.getters.timeline;
      let filename = encodeURIComponent(timeline.title + '.json');
      let element = document.createElement('a');

      element.setAttribute('href', 'data:application/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(timeline)));
      element.setAttribute('download', filename);

      element.style.display = 'none';
      document.body.appendChild(element);

      element.click();
      document.body.removeChild(element);
    }
  }
}
</script>
