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
            <div v-if="!Object.prototype.hasOwnProperty.call(editMode, timeline.id)" class="title">
                    <router-link :to="timeline.id.toString()"><div v-text="timeline.title"></div></router-link>
            </div>
            <input v-else type="text" class="title_edit title" v-model="editMode[timeline.id].title">
            <div class="description">
                 <div class="description_label label">
                     Description
                 </div>
                 <div class="description_text">
                    <div v-if="!Object.prototype.hasOwnProperty.call(editMode, timeline.id)" class="description" v-text="timeline.description"></div>
                    <textarea v-else class="description_edit description" v-model="editMode[timeline.id].description"></textarea>
                 </div>
            </div>
            <div class="subhead">
                 <div class="subhead_label label">
                     Subheading
                 </div>
                 <div class="subhead_text">
                    <div v-if="!Object.prototype.hasOwnProperty.call(editMode, timeline.id)" v-text="timeline.subhead" class="subhead"> </div>
                    <input v-else type="text" class="subhead_edit subhead" v-model="editMode[timeline.id].subhead">
                 </div>
            </div>


            <div class="numbers">
                <div class="case_count_label label">Cases</div>
                <div class="case_count value" v-text="timeline.case_count"></div>
                <div class="event_count_label label">Events</div>
                <div class="event_count value" v-text="timeline.event_count">0</div>
                <div class="id_label label">ID</div>
                <div class="id value" v-text="timeline.id">0</div>
            </div>
            <div class="edit">
                <button v-if="Object.prototype.hasOwnProperty.call(editMode, timeline.id)" class="btn btn-edit" @click="toggleEdit(timeline)">
                    <cancel-icon></cancel-icon>
                </button>
                <button v-else class="btn btn-edit" @click="toggleEdit(timeline)">
                    <edit-icon></edit-icon>
                </button>
            </div>
            <div class="delete">
                <button :disabled="!Object.prototype.hasOwnProperty.call(editMode, timeline.id)" class="btn btn-danger" @click="$store.dispatch('requestDeleteTimeline', timeline.id)">delete</button>
            </div>
            <div class="save">
                <button  class="btn btn-edit" @click="saveEdit(timeline.id)">
                    <save-icon v-if="Object.prototype.hasOwnProperty.call(editMode, timeline.id)"></save-icon>
                </button>
            </div>
          </div>
        </div>
      </div>
      <div v-else>
          Looks like you don't have any timelines... YET. Why don't you create one?
          <button type="button" class="btn btn-tertiary" data-toggle="modal" data-target="#add-case-modal" @click="$store.dispatch('requestCreateTimeline')">
            <add-icon></add-icon>
          </button>
      </div>

    </section>



  </main>

</template>

<script>
import AddIcon from '../../../../static/img/icons/add.svg';
import QuestionIcon from '../../../../static/img/icons/question.svg';
import EditIcon from '../../../../static/img/icons/edit.svg';
import SaveIcon from '../../../../static/img/icons/save.svg';
import CancelIcon from '../../../../static/img/icons/cancel.svg';

export default {
  name: 'Admin',
  components: {AddIcon, QuestionIcon, EditIcon, SaveIcon, CancelIcon},
    data() {
      return {
          editMode: {},
      }
    },
    methods: {
      toggleEdit(timeline) {
          if (Object.prototype.hasOwnProperty.call(this.editMode, timeline.id)) {
            this.$delete(this.editMode, timeline.id)
          } else {
              this.$set(this.editMode, timeline.id, {});
              this.$set(this.editMode[timeline.id], 'id', timeline.id);
              this.$set(this.editMode[timeline.id], 'title', timeline.title);
              this.$set(this.editMode[timeline.id], 'description', timeline.description);
              this.$set(this.editMode[timeline.id], 'subhead', timeline.subhead);
          }
      },
      saveEdit(id) {
          if (Object.prototype.hasOwnProperty.call(this.editMode, id)) {
            this.$store.dispatch('requestUpdateAdmin', this.editMode[id]).then(() => {
                    this.$delete(this.editMode, id);
                    this.$store.dispatch('requestTimelineList');
                }
            )
          }
      }

    }
};
</script>

