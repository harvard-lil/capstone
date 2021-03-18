<template>
  <div class="event-preview" v-if="event"
       :style="{border: '1px solid '+event.color}">
    <button type="button" @click="$parent.clearPreviewEvent()"
            class="close" aria-label="Close">
      <span aria-hidden="true">&times;</span>
    </button>

    <h5 :style="{borderBottom: '1px solid '+ this.event.color}">{{ event.name }}</h5>
    <template v-if="event.short_description">
      <div class="event-preview-body">
        <p v-for="desc in event.short_description.split('\n')" :key="desc">
          {{ desc }}
        </p>
      </div>
    </template>
    <button class="see-more btn btn-tertiary"
            @click="openModal(event)"
            data-toggle="modal"
            data-target="#readonly-modal">
      See more
    </button>
  </div>
</template>

<script>


export default {
  name: "EventPreview",
  props: ['event'],
  methods: {
    openModal() {
      this.$parent.$parent.openModal(this.event, 'event')
      this.$parent.clearPreviewEvent();
    },
  }
}
</script>
