<template>
  <main class="admin">
    <div class="top-menu">
      <h2><a href="../../">Labs:</a> Chronolawgic</h2>
      <h5 class="subhead">A legal timeline tool.</h5>
    </div>

    <section id="timeline" v-if="this.$store.state.user.is_authenticated === 'True'">
      <h6 class="timelines-title" v-if="this.$store.state.user.is_authenticated === 'True'" >Your timelines</h6>
      <template v-if="!this.$store.getters.availableTimelines.length">
        <p class="welcome">
          Welcome to Chronolawgic, the Caselaw Access Project tool for creating caselaw-focused timelines. To
          create your first timeline, click on the plus sign in the middle of the rectangle below, then click
          on the <span class="inline-icon"><edit-icon></edit-icon></span> symbol to set a title and description.
        </p>
      </template>
      <div class="timeline-assembly add-timeline">
        <div class="timeline-card">
          <button type="button" class="btn btn-tertiary" @click="$store.dispatch('requestCreateTimeline')">
            <add-icon></add-icon>
          </button>
        </div>
      </div>
      <template v-if="this.$store.getters.availableTimelines.length">
        <div class="timeline-assembly" v-for="timeline in this.$store.getters.availableTimelines"
             v-bind:key="timeline.id">
          <nav>
            <div class="editcancel" title="edit">
              <button v-if="Object.prototype.hasOwnProperty.call(editMode, timeline.id)"
                      class="btn btn-edit"
                      @click="toggleEdit(timeline)"
                      @keyup.esc="toggleEdit(timeline)">
                <cancel-icon></cancel-icon>
              </button>
              <button v-else class="btn btn-edit" @click="toggleEdit(timeline)">
                <edit-icon></edit-icon>
              </button>
            </div>
            <div class="delete" title="delete timeline">
              <button class="btn btn-edit"
                      v-if="Object.prototype.hasOwnProperty.call(editMode, timeline.id)"
                      @click="$store.dispatch('requestDeleteTimeline', timeline.id)">
                <delete-icon></delete-icon>
              </button>
            </div>
            <div class="save" title="save changes">
              <button class="btn btn-edit" @click="saveEdit(timeline.id)">
                <save-icon
                    v-if="Object.prototype.hasOwnProperty.call(editMode, timeline.id)"></save-icon>
              </button>
            </div>
          </nav>
          <div class="timeline-card">
            <div class="content">
              <header class="title">
                <h3 v-if="!Object.prototype.hasOwnProperty.call(editMode, timeline.id)">
                  <router-link :to="timeline.id.toString()"
                               v-text="timeline.title">
                  </router-link>
                </h3>
                <div class="title-edit" v-else>
                  <div class="label">Title</div>
                  <input type="text" @keyup.esc="toggleEdit(timeline)" @keyup.enter="saveEdit(timeline.id)"
                         class="title-input title" v-model="editMode[timeline.id].title">
                </div>
              </header>

              <div
                  :class="{'description': true, 'editmode': Object.prototype.hasOwnProperty.call(editMode, timeline.id)}">
                <p v-if="!Object.prototype.hasOwnProperty.call(editMode, timeline.id)"
                   v-text="timeline.description"></p>
                <div class="description-edit" v-else>
                  <div class="label">Description</div>
                  <textarea class="description-input" @keyup.esc="toggleEdit(timeline)"
                            v-model="editMode[timeline.id].description"></textarea>
                </div>
              </div>
            </div>
            <aside>
              <div class="stat">
                <div class="label">Cases</div>
                <div class="case_count value" v-text="timeline.case_count"></div>
              </div>
              <div class="stat">
                <div class="label">Events</div>
                <div class="event_count value" v-text="timeline.event_count">0</div>
              </div>
            </aside>
          </div>
        </div>
      </template>
    </section>
    <section class="not-logged-in" v-else>
      Welcome! To create Chronolawgic timelines, you must
      <a href="../../../user/login">log in</a> to your Caselaw Access Project account.
      For more information on Chronolawgic,
      <a href="../">click here</a>.
    </section>
    <br/>
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

