/* Functions */
function redraw_page(_page, _image, _canvas, _token_regions, _draw_word_confidence, _draw_ocr_text) {
    var ctx = _canvas.getContext("2d");
    ctx.drawImage(image, 0, 0);
    _token_regions.forEach(function () {
        if (wc < 0.5 && _draw_word_confidence) {
            ctx.globalAlpha = .6 - wc;
            red_level = 255 * wc + 127
            ctx.fillStyle = 'rgb(' + red_level + ', 0, 0)';
            ctx.fillRect(x, y, w, h);
        }
    })
}

function get_image_slice(image, x, y, w, h, scale = 2) {
    let canvas = document.getElementById("word_focus");
    canvas.height = h * scale + 20
    canvas.width = w * scale + 20
    let ctx = canvas.getContext("2d");
    ctx.drawImage(image, x - 5, y - 5, image.height + 10, image.width + 10, 0, 0, image.height * scale, image.width * scale)
}

function redraw_all() {
    pages.forEach(function (p) {
        // TODO
    })
}

function handle_correction(p) {
    // TODO
}

function import_saved_state(p) {
    // TODO
}

function handle_clicks(click_x, click_y, page_id, canvas, tokens) {
    tokens.forEach(function (word) {
        let block_id = word["block_id"];
        let line_label = word["line_label"];
        let wtext = word["word"];
        let wc = word["word_confidence"];
        let x = word["x"];
        let y = word["y"];
        let w = word["w"];
        let h = word["h"];
        // I was trying this with IsPointInPath but the math is so simple with rects that I figured this would be more efficient
        if ((click_x > x && click_x < x + w) && (click_y > y && click_y < y + h)) {
            document.getElementById("current_word").value = wtext
            document.getElementById("current_word_confidence").innerHTML = wc
            get_image_slice(images[page_id], x, y, w, h)
        }
    })
}

/* Set-Up */

let show_confidence = false
let show_ocr = false

const canvas_div = document.getElementById("canvas_div")
let canvases = {}
let images = {}
let scales = {}
let token_regions = {}

processed_pages.forEach(function (page, page_id) {
    canvases[page_id] = document.createElement("canvas");
    canvas_div.appendChild(canvases[page_id]);
    canvases[page_id].addEventListener('click', (e) => {
        var rect = e.target.getBoundingClientRect();
        var x = e.clientX - rect.left; //x position within the element.
        var y = e.clientY - rect.top;  //y position within the element.
        handle_clicks(x, y, page_id, canvases[page_id], token_regions[page_id])
    });
    images[page_id] = new Image();
    images[page_id].addEventListener("load", function () {
        var ctx = canvases[page_id].getContext("2d");
        canvases[page_id].width = images[page_id].width
        canvases[page_id].height = images[page_id].height
        ctx.drawImage(images[page_id], 0, 0);
        scales[page_id] = images[page_id].width / page_images[page_id]['width']
        token_regions[page_id] = []

        Object.keys(page).forEach(function (block_id) {
            Object.keys(page[block_id]).forEach(function (line_label) {
                page[block_id][line_label].forEach(function (word) {

                    let wc = word['wc']
                    let wtext = word['word']
                    let red_level = 255 * wc + 127
                    let x = word['rect'][0] * scales[page_id]
                    let y = word['rect'][1] * scales[page_id]
                    let w = word['rect'][2] * scales[page_id]
                    let h = word['rect'][3] * scales[page_id]
                    token_regions[page_id].push({
                        "block_id": block_id,
                        "line_label": line_label,
                        "word_confidence": wc,
                        "word": wtext,
                        "x": x,
                        "y": y,
                        "w": w,
                        "h": h,
                    })
                    if (wc < 0.5) {
                        ctx.globalAlpha = .6 - wc;
                        red_level = 255 * wc + 127
                        ctx.fillStyle = 'rgb(' + red_level + ', 0, 0)';
                        ctx.fillRect(x, y, w, h);
                    }
                });
            });
        });
    });
    images[page_id].setAttribute("src", page_images[page_id]['url']);
});
