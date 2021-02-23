<template>
    <div class="spans row">
        <div v-for="(col, index) in events" v-bind:key="year_value + index"
             :class="[
                 'event_col',
                 'ec_' + (index + 1),
                 'col-1',
                 'e' + year_value,
                  event_start(col.start_year) ? 'event_start' : '',
                  event_end(col.end_year) ? 'event_end' : '',
                  active ? 'event_end' : ''
             ]"
             :style="{
                'background-color': active ? col.color : '',
                'border-top': event_start(col.start_year) ? '1rem solid black' : '',
                'border-bottom': event_end(col.end_year) ? '1rem solid black' : '',
            }"
        ></div>
    </div>
</template>

<script>
    export default {
        name: "TimelineSlice",
        props: ['year_value', 'events'],
        methods: {
            event_start: function (comparison_year) {
                console.log(this.year_value, comparison_year)
                return (this.year_value === comparison_year)
            },
            event_end: function (comparison_year) {
                return (this.year_value === comparison_year)
            },
            active: function (comparison_year) {
                return (this.year_value === comparison_year)
            }
        }
    }
</script>

<style scoped>

</style>