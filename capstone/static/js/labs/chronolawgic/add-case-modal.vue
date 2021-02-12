<template>
  <div class="modal" id="add-case-modal" tabindex="-1" role="dialog">
    <div class="modal-dialog" role="document">
      <div class="modal-content">
        <div class="modal-header">
          <h5 class="modal-title">ADD CASE LAW</h5>
          <button type="button" class="close" data-dismiss="modal" aria-label="Close">
            <span aria-hidden="true">&times;</span>
          </button>
        </div>
        <form @submit.prevent="submitForm" class="modal-body">
          <div class="form-label-group">
            <input id="field-search-cap" placeholder="ENTER FULL TEXT OR CITATION" class="form-control">
            <label for="field-search-cap">ENTER FULL TEXT OR CITATION</label>
            <button role="button" class="btn btn-tertiary">SEARCH</button>
          </div>
          <div class="row">
            <div class="col-6">
              <div class="form-label-group">
                <input id="field-url" placeholder="URL" class="form-control">
                <label for="field-url">URL</label>
              </div>

            </div>
            <div class="col-6"></div>
          </div>
        </form>
        <div class="modal-footer">
          <button type="button" class="btn btn-primary">Save changes</button>
          <button type="button" class="btn btn-secondary" data-dismiss="modal">Close</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>

export default {
  name: "add-case-modal",
  components: {},
  methods: {
    submitForm() {
      console.log('submit form')
    }
  }
}
</script>

<style scoped>

</style>