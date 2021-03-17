<template>
  <div class="event-preview" v-if="event" :style="{border: '1px solid '+event.color}">
    <button type="button" @click="$parent.clearPreviewEvent()"
            class="close" data-dismiss="modal" aria-label="Close">
      <span aria-hidden="true">&times;</span>
    </button>

    <h5 :style="{borderBottom: '1px solid '+ this.event.color}">{{ event.name }}</h5>
    <template v-if="event.short_description"><p v-for="desc in event.short_description.split('\n')" :key="desc">{{ desc }}</p></template>
    <button class="btn btn-tertiary" @click.stop="$parent.openModal(event)">See more</button>
  </div>
</template>

<script>
export default {
  name: "EventPreview",
  props: ['event'],
}
</script>
