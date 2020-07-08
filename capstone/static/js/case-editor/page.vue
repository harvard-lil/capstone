<template>
        <canvas :id="page_id">
        </canvas>
</template>

<script>

    export default {
        props: [
            'page_id',
            'page_image',
            'blocks',
        ],
        data: function () {
            return {
                "image": new Image(),
                "scale": null,
            }
        },
        computed: {
            canvas_element: function () {
                return document.getElementById(this.page_id)
            },
        },
        methods: {
            handle_correction: function () {
                 this.$store.commit('update-word')
            },
            draw_page: function () {
                const page_component = this;
                const ctx = page_component.canvas_element.getContext("2d");
                ctx.clearRect(0, 0, page_component.canvas_element.width, page_component.canvas_element.height);
                ctx.globalAlpha = page_component.draw_ocr_text ? .2 : 1;
                ctx.drawImage(page_component.image, 0, 0);
                page_component.$store.state.word_regions[page_component.page_id].forEach(function (word) {
                    let wc = word["word_confidence"];
                    let wtext_array = word["word"];
                    let x = word["x"] * page_component.scale;
                    let y = word["y"] * page_component.scale;
                    let w = word["w"] * page_component.scale;
                    let h = word["h"] * page_component.scale;

                    if (page_component.$store.state.current_word == word) {
                        ctx.globalAlpha = 1;
                        ctx.strokeStyle = "green";
                        ctx.strokeRect(x, y, w, h);
                    }
                    if (page_component.$store.state.show_confidence && wc < 0.5) {
                        ctx.globalAlpha = .6 - wc;
                        let red_level = 255 * wc + 127;
                        ctx.fillStyle = 'rgb(' + red_level + ', 0, 0)';
                        ctx.fillRect(x, y, w, h);
                    }
                    if (page_component.$store.state.show_ocr) {
                        ctx.globalAlpha =1;
                        ctx.fillStyle = 'blue';
                        ctx.font = "20px Georgia";
                        let printable_word_value = '';
                        for (let wtext_entry in wtext_array) {
                            printable_word_value = printable_word_value + wtext_array[wtext_entry]['content']
                        }
                        ctx.fillText(printable_word_value, x, y + 12); //TODO: for some reason, on my browser, the text was offset by 12px?
                    }
                })
            },
            handle_page_clicks: function (click_x, click_y) {
                const page_component = this;
                page_component.$store.state.word_regions[page_component.page_id].forEach(function (word) {
                    //let block_id = word["block_id"];
                    //let line_label = word["line_label"];
                    let wtext_array = word["word"];
                    let x = word["x"] * page_component.scale;
                    let y = word["y"] * page_component.scale;
                    let w = word["w"] * page_component.scale;
                    let h = word["h"] * page_component.scale;
                    // I was trying this with IsPointInPath but the math is so simple with rects that I figured this would be more efficient
                    if ((click_x > x && click_x < x + w) && (click_y > y && click_y < y + h)) {
                        let printable_word_value = '';
                        for (let wtext_entry in wtext_array) {
                            printable_word_value = printable_word_value + wtext_array[wtext_entry]['content']
                        }
                        document.getElementById("current_word").value = printable_word_value;
                        page_component.$parent.get_image_slice(page_component.image, x, y, w, h);
                        page_component.$store.commit('set_current_word', word);
                        page_component.draw_page();
                    }
                })
            },
        },

        beforeMount() {
            const page_component = this;
            page_component.$store.state.word_regions[page_component.page_id] = []
            page_component.image.addEventListener("load", function () {
                Object.keys(page_component.blocks).forEach(function (block_id) {
                    Object.keys(page_component.blocks[block_id]).forEach(function (line_label) {
                        page_component.blocks[block_id][line_label].forEach(function (word) {
                            page_component.$store.state.word_regions[page_component.page_id].push({
                                "page_id": page_component.page_id,
                                "block_id": block_id,
                                "line_label": line_label,
                                "word_confidence": word['wc'],
                                "word": word['word'],
                                "x": word['rect'][0],
                                "y": word['rect'][1],
                                "w": word['rect'][2],
                                "h": word['rect'][3],
                                'corrections': []
                            })
                        });
                    });
                });
                page_component.canvas_element.width = page_component.image.width;
                page_component.canvas_element.height = page_component.image.height;
                page_component.scale = page_component.image.width / page_component.page_image['width'];
                page_component.draw_page()
            });

        },
        mounted() {
            const page_component = this;
            page_component.image.setAttribute("src", page_component.page_image['url']);
            page_component.canvas_element.addEventListener('click', (e) => {
                let rect = e.target.getBoundingClientRect();
                let x = e.clientX - rect.left; //x position within the element.
                let y = e.clientY - rect.top;  //y position within the element.
                page_component.handle_page_clicks(x, y)
            });
            page_component.$store.watch((state) => state.show_ocr, () => {
                page_component.draw_page();
            })
            page_component.$store.watch((state) => state.show_confidence, () => {
                page_component.draw_page();
            })
        },
    }
</script>
