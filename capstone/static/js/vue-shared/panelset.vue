<script>
  import Vue from 'vue';

  /*
    This Panelset mixin creates a set of panels that can each be hidden or shown with a set of buttons. Clicking one
    button shows that panel and hides any existing panels. Example:
    <template>
      <panelset-button panel-id="options" :current-panel="currentPanel" additional-button-attrs...>
        button contents
      </panelset-button>
      <panelset-panel panel-id="options" :current-panel="currentPanel">
        panel contents
      </panelset-panel>
    </template>
    <script>
      export default {
        mixins: [Panelset]
      }
    <//script>
  */
  export default {
    components: {
      PanelsetButton: Vue.component('panelset-button', {
        props: ['panelId', 'currentPanel'],
        template: `
          <button class="btn-secondary"
                  type="button"
                  @click="$parent.currentPanel = (currentPanel === panelId?null:panelId)"
                  :aria-expanded="currentPanel === panelId"
                  :aria-controls="\`\${panelId}Panel\`">
            <slot></slot>
          </button>
        `
      }),
      PanelsetPanel: Vue.component('panelset-panel', {
        props: ['panelId', 'currentPanel'],
        template: `
          <div class="card"
               :id="\`\${panelId}Panel\`"
               v-if="currentPanel === panelId"
               tabindex="-1"
               @keydown.esc="$parent.currentPanel = null">
            <div class="card-body">
              <button type="button"
                      @click="$parent.currentPanel = null"
                      class="close h40.7em "
                      :aria-controls="\`\${panelId}Panel\`"
                      aria-label="Close">
                <span aria-hidden="true">&times;</span>
              </button>
              <slot></slot>
            </div>
          </div>
        `,
      }),
    },
    data: function () {
      return {
        currentPanel: null,
      }
    },
  }
</script>