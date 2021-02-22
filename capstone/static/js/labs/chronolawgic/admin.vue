<template>
  <main>
    <div class="timelines">
      <h3>Your Timelines</h3>
      <div v-if="this.$store.getters.availableTimelines">
        <div class="timeline" v-for="timeline in this.$store.getters.availableTimelines" v-bind:key="timeline.id">
          <div class="id" v-text="timeline.id"></div>
          <div class="title" v-text="timeline.title"></div>
          <div class="subhead" v-text="timeline.subhead"></div>
          <div class="button btn-edit">
            <button class="btn btn-primary">edit</button>
          </div>
          <div class="button btn-delete">
            <button class="btn btn-danger" @click="$store.dispatch('requestDeleteTimeline', timeline.id)">delete</button>
          </div>
        </div>
      </div>
      <div v-else>
        Looks like you don't have any timelines... YET. Why don't you create one?
      </div>
      <div class="timeline">
        <div class="button btn-hidden"></div>
        <div class="button btn-create">
          <button class="btn-default" @click="$store.dispatch('requestCreateTimeline')">create</button>
        </div>
      </div>
    </div>
    <br/>
  </main>

</template>

<script>

export default {
  name: 'Admin',
};
</script>

<style>
h3 {
  font-weight: bold;
  margin-bottom: 2rem;
}

.timelines {
  max-width: 50rem;
  margin-left: auto;
  margin-right: auto;
  margin-top: 5rem;
}

.timeline {
  display: grid;
  grid-template-areas: "id title subhead button-one button-two";
  grid-template-columns: 1fr 3fr 4fr 2fr;
  margin-top: 1rem;
}

.id {
  grid-area: id;
}

.title {
  grid-area: title;
  font-family: source-serif;
  font-weight: bold;
  font-size: 2rem;
}

.subhead {
  grid-area: subhead;
}

.btn-edit {
  grid-area: button-one;
}

.btn-delete {
  grid-area: button-two;
}

.btn-hidden {
  grid-area: button-one;
}

.btn-create {
  grid-area: button-two;
}
</style>