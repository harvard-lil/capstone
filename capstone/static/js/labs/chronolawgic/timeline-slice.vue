<template>
    <div class="spans row">

        <div v-for="(event_data, index) in events" v-bind:key="year_value + index"
             :tabindex="parseInt(year_value) === parseInt(event_data.start_year) ? '0' : '-1'"
             :class="[
                 'event_col',
                 'ec_' + (index + 1),
                 'col-1',
                 'e' + year_value,
                  parseInt(year_value) === parseInt(event_data.start_year) ? 'event_start' : '',
                  parseInt(year_value) === parseInt(event_data.end_year) ? 'event_end' : '',
             ]"
             :style="{
                'background-color': event_data.color,
                'border-top': parseInt(year_value) === parseInt(event_data.start_year) ? '1rem solid black' : '',
                'border-bottom': parseInt(year_value) === parseInt(event_data.end_year) ? '1rem solid gray' : '',
            }"
            @click="toggleEventModal(event_data)">
                <event-modal
                    v-if="showEventDetails"
                    data-toggle="modal"
                    data-target="event-modal"
                    :modal.sync="showEventDetails"
                    :event="event"
                    :shown="showEventDetails">
                </event-modal>
        </div>
    </div>
</template>

<script>
    import EventModal from "./event-modal";

    export default {
        name: "TimelineSlice",
        components: { EventModal },
        props: ['year_value', 'events'],
        methods: {
            toggleEventModal(item) {
                this.showEventDetails =  !this.showEventDetails;
                this.event = item
            },
        },
        data() {
            return {
                showEventDetails: false,
            }
        }
    }
</script>

<style scoped>

</style>