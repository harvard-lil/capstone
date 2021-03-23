import Vue from 'vue'

export default Vue.component('YearLabel', {
  template: `
    <svg version="1.1" id="Layer_1" width="125px" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 250 125" xml:space="preserve" @mouseover="yearHoverToggle(true)" @mouseleave="yearHoverToggle(false)">
      <rect style="fill:#FFFFFF;" x="0" y="34" height="60" width="178" />
      <line v-if="!yearHover" style="fill:none;stroke:#363636;stroke-width:4;stroke-miterlimit:10;" x1="29.5" y1="62.5" x2="50.5" y2="62.5"/>
      <text style="font-family: 'source-code', monospace;" transform="matrix(2 0 0 2 80 75)" >{{year}}</text>
      <g id="circles" v-if="yearHover">
        <g style="cursor:pointer;" @click="addCase(year)">
          <circle style="fill:#FFF;stroke:#363636;stroke-width:4;stroke-miterlimit:10;" cx="40" cy="63.2" r="20"/>
          <line style="fill:none;stroke:#363636;stroke-width:4;stroke-miterlimit:10;" x1="40" y1="52" x2="40" y2="73"/>
          <line style="fill:none;stroke:#363636;stroke-width:4;stroke-miterlimit:10;" x1="29.5" y1="62.5" x2="50.5" y2="62.5"/>
        </g>
        <g style="cursor:pointer;" @click="addEvent(year)">
          <circle style="fill:#EEE;stroke:#363636;stroke-width:4;stroke-miterlimit:10;" cx="210" cy="63.2" r="20"/>
          <line style="fill:none;stroke:#363636;stroke-width:4;stroke-miterlimit:10;" x1="210" y1="52" x2="210" y2="73"/>
          <line style="fill:none;stroke:#363636;stroke-width:4;stroke-miterlimit:10;" x1="199.5" y1="62.5" x2="220.5" y2="62.5"/>
        </g>
      </g>
    </svg>`,
  props: ['year'],
  data() {
    return { yearHover: false }
  },
  methods: {
    addCase(year) {
      this.$parent.$parent.openModal({decision_date: year + '-01-01'}, 'case');
    },
    addEvent(year) {
      this.$parent.$parent.openModal({start_date: year + '-01-01'}, 'event');
    },
    yearHoverToggle(newHoverState) {
      this.yearHover=this.$store.state.isAuthor ? newHoverState : false;
    }
  }
});


