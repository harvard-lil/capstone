<template>
  <main class="admin">
        <div class="row top-menu">
      <div class="header-section case-law-section">
        <span>TIMELINES</span>
        <button type="button" class="btn btn-tertiary" data-toggle="modal" data-target="#add-case-modal" @click="$store.dispatch('requestCreateTimeline')">
          <add-icon></add-icon>
        </button>
      </div>
      <div class="header-section other-events-section">
          <span>WHERE AM I?</span>
          <a href=".." class="icon-link" alt="What is this interface?"><question-icon></question-icon></a>
      </div>
      <div class="key-column">
      </div>
    </div>
    <section id="timeline">
      <div v-if="this.$store.getters.availableTimelines">
        <div class="timelines">
          <div class="timeline" v-for="timeline in this.$store.getters.availableTimelines" v-bind:key="timeline.id">
            <!--<div class="id" v-text="timeline.id"></div>-->
            <div class="title">
              <router-link :to="timeline.id.toString()"><div v-text="timeline.title"></div></router-link>
            </div>
            <div class="description" v-text="timeline.long_description"></div>
            <div class="numbers">Soon</div>
            <div class="buttons">
              <div class="button btn-edit">
                <button class="btn btn-primary">edit</button>
              </div>
              <div class="button btn-delete">
                <button class="btn btn-danger" @click="$store.dispatch('requestDeleteTimeline', timeline.id)">delete</button>
              </div>
            </div>
          </div>
        </div>
      </div>
      <div v-else>
          Looks like you don't have any timelines... YET. Why don't you create one?
      </div>

    </section>



  </main>

</template>

<script>
import AddIcon from '../../../../static/img/icons/add.svg';
import QuestionIcon from '../../../../static/img/icons/question.svg';

export default {
  name: 'Admin',
  components: {AddIcon, QuestionIcon}
};
</script>

