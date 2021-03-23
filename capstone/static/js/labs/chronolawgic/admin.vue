<template>
  <main class="admin">
    <div class="row top-menu">
      <h3>Timelines
        <a href=".." class="btn btn-tertiary info icon-link">?</a>
      </h3>
      <div v-if="this.$store.state.user.is_authenticated === 'True'" class="add-timeline">
        <button type="button" class="btn btn-tertiary" @click="$store.dispatch('requestCreateTimeline')">
          Add a timeline
          <add-icon></add-icon>
        </button>
      </div>
      <div v-else class="add-timeline">
        You need to be logged in to your free case.law account to use Chronolawgic timelines. For more information on this tool,
        <a href="../">click here</a>.
      </div>
    </div>
    <section id="timeline">
      <div class="timelines">
        <div v-if="this.$store.getters.availableTimelines.length">
          <div class="timeline" v-for="timeline in this.$store.getters.availableTimelines" v-bind:key="timeline.id">
            <div v-if="!Object.prototype.hasOwnProperty.call(editMode, timeline.id)" class="title">
              <router-link :to="timeline.id.toString()"
                           v-text="timeline.title">
              </router-link>
            </div>
            <input v-else type="text" class="title_edit title" v-model="editMode[timeline.id].title">
            <div class="btn-group">
              <div class="edit" title="edit">
                <button v-if="Object.prototype.hasOwnProperty.call(editMode, timeline.id)" class="btn btn-edit"
                        @click="toggleEdit(timeline)">
                  <cancel-icon></cancel-icon>
                </button>
                <button v-else class="btn btn-edit" @click="toggleEdit(timeline)">
                  <edit-icon></edit-icon>
                </button>
              </div>
              <div class="delete" title="delete timeline">
                <delete-icon v-if="Object.prototype.hasOwnProperty.call(editMode, timeline.id)"
                             @click="$store.dispatch('requestDeleteTimeline', timeline.id)"></delete-icon>
              </div>
              <div class="save" title="save changes">
                <button class="btn btn-edit" @click="saveEdit(timeline.id)">
                  <save-icon v-if="Object.prototype.hasOwnProperty.call(editMode, timeline.id)"></save-icon>
                </button>
              </div>
            </div>
            <div class="description" v-if="timeline.description || editMode[timeline.id]">
              <div class="description_label label">
                Description
              </div>
              <div class="description_text">
                <div v-if="!Object.prototype.hasOwnProperty.call(editMode, timeline.id)" class="description"
                     v-text="timeline.description"></div>
                <textarea v-else class="description_edit description"
                          v-model="editMode[timeline.id].description"></textarea>
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
          </div>
        </div>
      </div>
    </section>


  </main>

</template>

<script>
import AddIcon from '../../../../static/img/icons/plus-circle.svg';
import EditIcon from '../../../../static/img/icons/edit.svg';
import SaveIcon from '../../../../static/img/icons/save.svg';
import CancelIcon from '../../../../static/img/icons/cancel.svg';
import DeleteIcon from '../../../../static/img/icons/trash-2.svg';

export default {
  name: 'Admin',
  components: {AddIcon, EditIcon, SaveIcon, CancelIcon, DeleteIcon},
  data() {
    return {
      editMode: {},
      timelines: {}
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
  },
};
</script>

