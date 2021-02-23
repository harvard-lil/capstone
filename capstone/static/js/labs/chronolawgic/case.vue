<template>
    <article class="case">
        <header>
           {{ case_data.title }}
        </header>
        <div class="links">
            <a href="details">details</a><br>
            <a href="#">read case</a></div>
    </article>
</template>

<script>
    export default {
        name: "Case",
        props: ['case_data', 'year_value']
    }
</script>

<style scoped>

</style>