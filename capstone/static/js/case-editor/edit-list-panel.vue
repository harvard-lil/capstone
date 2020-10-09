<template>
  <div class="row">
    <div class="count col-1">

    </div>
    <div class="col-11">
      <ol reversed class="edited-word-list">
        <li>
          <div class="row edit-entry edit-head">
            <div class="col-1 count_col"><span class="pencil">&#x270E;</span>{{ Object.keys(editedWords).length }}</div>
            <div class="col-2 offset-9 clear_col">
              <span class="edit-delete clear_edits" @click="$parent.clearEdits">clear</span>
            </div>
          </div>
        </li>
        <li  v-for="word in editedWords" :key="word.id">

          <div class="row edit-entry">
            <div class="col-5 edit-word word" @click="$store.commit('setCurrentWord', word)">{{word.originalString}}</div>
            <div class="col-5 edit-word word" @click="$store.commit('setCurrentWord', word)">{{word.string}}</div>
            <div class="col-2 edit-controls"><span class="edit-delete" @click="$store.commit('removeEdit', word)">&#8855;</span></div>
          </div>
        </li>
      </ol>
    </div>
  </div>
</template>

<script>
  import { mapState } from 'vuex'
  export default {
    computed: mapState(['editedWords']),
  }
</script>
