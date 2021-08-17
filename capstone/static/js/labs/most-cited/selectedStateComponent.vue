<template>
  <li class="states-info">
    <!--Name of case (linked to case on CAP)-->
    <a :href="caseobject[2]">
      <b>{{ casename }}</b>
    </a>
    <template v-if="jurisdiction">,
      <b> {{ jurisdiction }}</b>
    </template>
    <!--decision date if available-->
    <template v-if="caseobject[3]">
      ({{ caseobject[3] }})
    </template>
    <!--how many times cited-->
    cited {{ caseobject[1] }} times
  </li>
</template>

<script>
export default {
  name: "selectedStateComponent",
  props: ["caseobject", "casename", "jurisdiction"],
}
</script>
