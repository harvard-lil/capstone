<template>
  <div class="event-preview" v-if="event" :style="{border: '1px solid '+event.color}">
    <button type="button" @click="$parent.clearPreviewEvent()"
            class="close" data-dismiss="modal" aria-label="Close">
      <span aria-hidden="true">&times;</span>
    </button>

    <h5 :style="{borderBottom: '1px solid '+event.color}">{{ event.name }}</h5>
    <p v-for="desc in event.short_description.split('\n')" :key="desc">{{ desc }}</p>
    <button class="btn btn-tertiary" @click="$parent.openModal(event)">See more</button>
  </div>
</template>

<script>
export default {
  name: "EventPreview",
  props: ['event'],
}
</script>
