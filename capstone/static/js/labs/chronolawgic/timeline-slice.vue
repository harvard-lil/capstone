<template>
    <div class="spans row">
         <div v-for="(event_data, index) in event_list" v-bind:key="year_value + index"
              :class="[ 'event_col', 'ec_' + (index + 1), 'col-1', 'e' + year_value, ]">
            <div class="fill" v-if="Object.keys(event_data).length > 0"
                    :tabindex="parseInt(year_value) === event_data.start_date.getUTCFullYear() ? '0' : '-1'"
                 :style="{
                    'background-color': event_data.color,
                    'border-top': parseInt(year_value) === event_data.start_date.getUTCFullYear() ? '1rem solid black' : '',
                    'border-bottom': parseInt(year_value) === event_data.end_date.getUTCFullYear() ? '1rem solid gray' : '',
                    'min-height': '1rem'
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
    </div>
</template>

<script>
    import EventModal from "./event-modal";

    export default {
        name: "TimelineSlice",
        components: { EventModal },
        props: ['year_value', 'event_list'],
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
        },
    }
</script>

<style scoped>

</style>