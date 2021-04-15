<template>
  <nav id="main-nav" aria-label="main">
    <div class="branding">
      <a class="nav-branding" :href="urls.home" aria-label="Caselaw Access Project Home"></a>
    </div>
    <button id="burger-icon">
      <div class="burger-item"></div>
      <div class="burger-item"></div>
      <div class="burger-item"></div>
    </button>

    <div class="nav-content">
      <ul class="nav">
        <li class="nav-item nav-search-item">
          <input placeholder="Search caselaw" v-model="query" @keyup.enter="searchCAP">
          <button type="submit" @click="searchCAP" class="btn search-icon">
            <search-icon></search-icon>
          </button>
        </li>
        <li class="nav-item dropdown" id="nav-tools">
          <a class="nav-link dropdown-toggle"
             href="#" id="navbar-dropdown-tools"
             role="button"
             aria-haspopup="true"
             aria-expanded="false">
            Caselaw
          </a>
          <div class="dropdown-menu" aria-labelledby="navbar-dropdown-tools">
            <a class="dropdown-item" :href="urls.tools">Tools overview</a>
            <a class="dropdown-item" :href="urls.api_root">API</a>
            <a class="dropdown-item" :href="urls.cite">Read Caselaw</a>
            <a class="dropdown-item" :href="urls.bulk">Bulk Data</a>
            <a class="dropdown-item" :href="urls.search">Search</a>
          </div>
        </li>
        <li class="nav-item dropdown" id="nav-contact">
          <a class="nav-link dropdown-toggle"
             href="#" id="navbar-dropdown-docs"
             role="button"
             aria-haspopup="true"
             aria-expanded="false">Support/docs </a>
          <div class="dropdown-menu" aria-labelledby="navbar-dropdown-docs">
            <a class="dropdown-item" :href="urls.docs">Docs Overview </a>
            <a class="dropdown-item" :href="urls.docs + 'site_features/api'">API</a>
            <a class="dropdown-item" :href="urls.docs + 'site_features/bulk'">Bulk Data</a>
            <a class="dropdown-item" :href="urls.docs + 'site_features/search'">Search</a>
          </div>
        </li>
        <li class="nav-item dropdown" id="nav-gallery">
          <a class="nav-link dropdown-toggle"
             href="#" id="navbar-dropdown-gallery"
             role="button"
             aria-haspopup="true"
             aria-expanded="false">
            Gallery
          </a>

          <div class="dropdown-menu" aria-labelledby="navbar-dropdown-gallery">
            <a class="dropdown-item" :href="urls.gallery">Gallery home</a>
            <a class="dropdown-item" :href="urls.labs">CAP Labs</a>
            <a class="dropdown-item" :href="urls.gallery + '#research-results'">Research Results</a>
            <a class="dropdown-item" :href="urls.gallery + '#coursework'">Coursework</a>
            <a class="dropdown-item" :href="urls.gallery + '#fun-stuff'">Fun Stuff</a>
            <a class="dropdown-item" :href="urls.gallery + '#applications'">Applications</a>
            <a class="dropdown-item" :href="urls.gallery + '#applications-third-party'">Applications Third Party</a>
            <a class="dropdown-item" :href="urls.gallery + '#tutorials'">Tutorials</a>
          </div>
        </li>
        <li class="nav-item dropdown" id="nav-about">
          <a class="nav-link dropdown-toggle"
             href="#" id="navbar-dropdown-about"
             role="button"
             aria-haspopup="true"
             aria-expanded="false">
            About
          </a>

          <div class="dropdown-menu" aria-labelledby="navbar-dropdown-about">
            <a class="dropdown-item" :href="urls.about">About CAP</a>
            <a class="dropdown-item" :href="urls.contact">Contact</a>
          </div>
        </li>
        <li class="nav-item" id="nav-account">
          <a v-if="user.is_authenticated === 'True'"
             :href="urls.user_details" class="nav-link nav-link-icon">
            <user-icon></user-icon>
            <div class="x-small">Account</div>
          </a>
          <a v-else :href="urls.login" class="nav-link nav-link-icon">
            <user-icon></user-icon>
            <div class="x-small">Log in</div>
          </a>
        </li>
      </ul>
    </div>
  </nav>
</template>

<script>
import UserIcon from '../../../static/img/icons/user.svg';
import SearchIcon from '../../../static/img/icons/search.svg';

export default {
  name: "main.vue",
  components: {
    UserIcon,
    SearchIcon
  },
  data() {
    return {
      query: '',
    }
  },
  methods: {
    searchCAP() {
      window.location.href = this.urls.search + '#/cases?search=' + this.query + '&page=1&ordering=relevance'
    }
  },
  beforeCreate: function () {
    /*
      Here we get a number of variables defined in the django template
     */
    this.urls = nav_urls;  // eslint-disable-line
    this.user = nav_user; // eslint-disable-line
  },

}
</script>

<style scoped>

</style>