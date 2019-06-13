<template>
  <div>
    <button class="btn-create btn-primary d-flex align-items-center">
      <slot></slot>
      <span v-if="showLoading"
            class="spinner-border spinner-border-sm"
            role="status"
            aria-hidden="true"></span>
    </button>
    <span v-if="showLoading"
          id="loading-focus"
          class="sr-only"
          tabindex="-1">Loading</span>
  </div>
</template>
<script>
  export default {
    props: ['showLoading'],
    watch: {
      showLoading: function(newVal, oldVal) {  // eslint-disable-line no-unused-vars
        if(newVal)
          setTimeout(()=>{
            const loadingMessage = document.querySelector('#loading-focus');
            if (loadingMessage)
              loadingMessage.focus();
          });
      }
    }
  }
</script>