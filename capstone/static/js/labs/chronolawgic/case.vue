<template>
    <article class="case" @click="toggleEventModal(case_data)" tabindex="0">
        <event-modal
                v-if="showEventDetails"
                data-toggle="modal"
                data-target="event-modal"
                :modal.sync="showEventDetails"
                :event="event"
                :shown="showEventDetails">
        </event-modal>

        <header>
           {{ case_data.name }}
        </header>
        <section class="subhead">
            {{ case_data.subhead }}
        </section>
        <section class="desc">
            {{ case_data.short_description }}
        </section>
    </article>
</template>

<script>
    import EventModal from './event-modal.vue';
    export default {
        name: "Case",
        components: { EventModal },
        props: ['case_data', 'year_value'],
        data() {
          return {
              showEventDetails: false
          }
        },
        methods: {
            toggleEventModal(item) {
                this.showEventDetails =  !this.showEventDetails;
                this.event = item
            },
        }

    }
</script>

