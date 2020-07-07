<template>
    <div class="grid-container">
        <div class="controls grid-item">
            <div class="row margin-top-4">
                <div class="col">
                    <div class="sticky-top">
                        <div class="row">
                            <div class="col">
                                <input type="checkbox" v-model="show_ocr" id="show_ocr">
                                <label for="show_ocr">See OCR</label>
                                <br>
                                <input type="checkbox" v-model="show_confidence" id="see_wc">
                                <label for="see_wc">See WC</label>
                            </div>
                            <div class="col">

                            </div>
                        </div>
                        <div class="row">
                            <div class="col">
                                <canvas id="word_focus" height="45px"></canvas>
                            </div>
                        </div>
                        <div class="row">
                            <div class="col">
                                <input type="text" :value="printable_word_value" id="current_word">
                                <small><small>
                                    (confidence: <span id="current_word_confidence">{{this.$store.state.current_word.word_confidence}}</span>)
                                </small></small>
                                <button id="apply_correction">Apply</button>
                                <button id="add_soft_hyphen">Add Soft Hyphen(⧟)</button>
                            </div>
                        </div>

                        <div class="row mt-4">
                            <div class="col">
                                <input type="text" :value="this.$store.state.case_info.fields.name"
                                       placeholder="case name">
                                <input type="text" :value="this.$store.state.case_info.fields.docket_number"
                                       placeholder="docket number">
                                <input type="text"
                                       :value="this.$store.state.case_info.fields.decision_date_original"
                                       placeholder="decision date string">
                                <button>Modify Metadata</button>
                            </div>
                        </div>
                        <div class="row mt-4">
                            <div class="col">
                                <button class="danger">Save Case To Database</button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        <div id="canvas_div grid-item">
            <page v-for="pg in this.$store.state.processed_pages"
                  :key="pg[0]"
                  :page_id="pg[0]"
                  :page_image="pg[1]['image']"
                  :blocks="pg[1]['blocks']"/>
        </div>
    </div>
</template>

<script>
    import Page from './page.vue'
    export default {
        components: {Page},
        methods: {
            handle_correction: function () {
                //have the store process the correction
            },
            save_case: function () {
                 this.$store.commit('save')
            },
            get_image_slice: function (_image, _x, _y, _w, _h, _scale = 2) {
                let canvas = document.getElementById("word_focus");
                canvas.height = _h * _scale + 20;
                canvas.width = _w * _scale + 20;
                let ctx = canvas.getContext("2d");
                ctx.drawImage(_image, _x - 5, _y - 5, _image.height + 10, _image.width + 10, 0, 0, _image.height * _scale, _image.width * _scale)
            },
        },
        computed: {
            show_ocr: {
                get: function () { return this.$store.state.show_ocr; },
                set: function () { this.$store.commit('toggle_show_ocr'); }
            },
            show_confidence: {
                get: function () { return this.$store.state.show_confidence; },
                set: function () { this.$store.commit('toggle_show_confidence'); }
            },
            printable_word_value: {
                /*
                    TODO: This isn't the right solution here. v-for with word parts that have separate inputs seems
                    weird too. Maybe a data transfer format change?
                 */
                get: function () {
                        let printable = ''
                        for (let wd in this.$store.state.current_word.word) {
                            printable = '' + printable + this.$store.state.current_word.word[wd].content
                        }
                        return printable;
                    }
            },
        },
        mounted() {
            let control_component = this;
            const current_word_element = document.getElementById("current_word")

            document.getElementById("apply_correction").addEventListener("click", function () {
                let updated_word = current_word_element.valueOf();
                if (updated_word !== control_component.current_word['word']) {
                    control_component.handle_correction(this.$store.state.current_word, updated_word);
                }
            });

            document.getElementById("add_soft_hyphen").addEventListener("click", function () {
                current_word_element.value = current_word_element.value + "⧟";
            });
        }
    }
</script>