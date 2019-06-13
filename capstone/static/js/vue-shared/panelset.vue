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
        props: ['panelId', 'currentPanel', 'title'],
        template: `
          <button class="btn-secondary"
                  :id="\`\${panelId}PanelButton\`"
                  type="button"
                  @click="onClick"
                  @blur="onBlur"
                  :aria-expanded="currentPanel === panelId"
                  :aria-controls="currentPanel === panelId ? \`\${panelId}Panel\` : false">
            <slot></slot>
          </button>
        `,
        methods: {
          onClick() {
            if (this.currentPanel === this.panelId) {
              this.$parent.currentPanel = null;
            } else {
              this.$parent.currentPanel = this.panelId;
              this.focusInPanel();
            }
          },
          onBlur() {
            if (this.currentPanel === this.panelId) {
              this.focusInPanel();
            }
          },
          focusInPanel(){
            /* focus on first element inside panel */
            Vue.nextTick().then(() => {
              const firstFocus = document.getElementById(
                `${this.panelId}Panel`
              ).querySelectorAll(
                'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
              )[0];
              firstFocus.focus();
            });
          },
        }
      }),
      PanelsetPanel: Vue.component('panelset-panel', {
        props: ['panelId', 'currentPanel'],
        template: `
          <div class="card"
               :id="\`\${panelId}Panel\`"
               v-if="currentPanel === panelId"
               tabindex="-1"
               @keydown.esc="closeButtonClick">
            <div class="card-body">
              <slot></slot>
              <button type="button"
                      @click="closeButtonClick"
                      class="close"
                      @blur.prevent="closeButtonBlur"
                      :aria-controls="\`\${panelId}Panel\`"
                      :aria-label="\`close \${panelId} panel\`">
                <span aria-hidden="true">&times;</span>
              </button>
            </div>
          </div>
        `,
        methods: {
          focusOnButton() {
            document.getElementById(`${this.panelId}PanelButton`).focus();
          },
          closeButtonClick() {
            this.$parent.currentPanel = null;
            this.focusOnButton();
          },
          closeButtonBlur() {
            this.focusOnButton();
          },
        }
      }),
    },
    data: function () {
      return {
        currentPanel: null,
      }
    },
  }
</script>