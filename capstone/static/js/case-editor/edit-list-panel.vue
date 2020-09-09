<template>
  <div>
    <h4 class="section-title">edits</h4>
    <div class="edited-word-list mt-3">
      <div class="row edit-entry" v-for="word in editedWords" :key="word.id">
        <div class="col-5 word" @click="$store.commit('setCurrentWord', word)">{{word.originalString}}</div>
        <div class="col-6 word" @click="$store.commit('setCurrentWord', word)">{{word.string}}</div>
        <div class="col-1 edit-controls"><span class="edit-delete" @click="$store.commit('removeEdit', word)">&#8855;</span></div>
      </div>
    </div>
  </div>
</template>

<script>
  import { mapState } from 'vuex'

  export default {
    computed: mapState(['editedWords']),
  }
</script>
