<template>
    <article class="case" @click="showEventModal(case_data)">
        <header>
           {{ case_data.title }}
        </header>
        <div class="links">
            <a href="details">details</a><br>
            <a href="#">read case</a></div>
    </article>
</template>

<script>
    import EventModal from './event-modal.vue';
    export default {
        name: "Case",
        components: [EventModal],
        props: ['case_data', 'year_value'],
        methods: {
            showEventModal(item) {
                console.log("showeventmodal", item.name)
                this.showEventDetails = true
                this.event = item
            }
        }
    }
</script>

<style scoped>

</style>