<template>
    <div class="year" v-bind:class="{ collapsible: collapsible }">
        <div class="incidental" >
            <case v-for="case_data in year_data.case_list" :year_value="year_value" :case_data="case_data" v-bind:key="case_data.id"></case>
        </div>
        <div class="year_scale">
            <div class="left-line">
                <hr class="left-rule">
            </div>
            <div class="year">
                {{year_value}}
            </div>
            <div class="right-line">
                <hr>
            </div>
        </div>
        <TimeLineSlice :events="year_data.event_list" :year_value="year_value"></TimeLineSlice>
    </div>
</template>

<script>
    import TimeLineSlice from './timeline-slice';
    import Case from './case';
    export default {
        name: "Year",
        components: {
            TimeLineSlice,
            Case,
        },
        props: ['year_data', 'year_value'],
        computed: {
            collapsible: function () {
                const event_count = this.year_data.event_list.reduce((acc,element) => acc + Object.keys(element).length, 0);
                return (event_count + this.year_data.case_list.length === 0)
            }
        },
    }
</script>

<style scoped>

</style>