/* Initialize*/

// eslint-disable-next-line
const page_images = import_page_images_from_django_template;
// eslint-disable-next-line
const processed_pages = import_processed_pages_from_django_template;

var show_confidence = document.getElementById("see_wc").checked
var show_ocr = document.getElementById("see_ocr").checked
var current_word = null

/* Functions */
function draw_page(_page, _image, _canvas, _word_regions_on_page, _draw_word_confidence, _draw_ocr_text, _highlight_word=null) {
    var ctx = _canvas.getContext("2d");
    ctx.clearRect(0, 0, _canvas.width, _canvas.height);
    ctx.globalAlpha = _draw_ocr_text ? .2 : 1;
    ctx.drawImage(_image, 0, 0);
    _word_regions_on_page.forEach(function (word) {
        let wc = word["word_confidence"];
        let wtext = word["word"];
        let x = word["x"];
        let y = word["y"];
        let w = word["w"];
        let h = word["h"];

        if (_highlight_word == word) {
            ctx.strokeStyle = "green";
            ctx.strokeRect(x, y, w, h);
        }
        if (_draw_word_confidence && wc < 0.5) {
            ctx.globalAlpha = .6 - wc;
            let red_level = 255 * wc + 127
            ctx.fillStyle = 'rgb(' + red_level + ', 0, 0)';
            ctx.fillRect(x, y, w, h);
        }
        if (_draw_ocr_text) {
            ctx.globalAlpha =1;
            ctx.fillStyle = 'blue';
            ctx.font = "20px Georgia";
            ctx.fillText(wtext, x, y + 12); //TODO: for some reason, on my browser, the text was offset by 12px?
        }
    })
}

function get_image_slice(_image, _x, _y, _w, _h, _scale = 2) {
    let canvas = document.getElementById("word_focus");
    canvas.height = _h * _scale + 20
    canvas.width = _w * _scale + 20
    let ctx = canvas.getContext("2d");
    ctx.drawImage(_image, _x - 5, _y - 5, _image.height + 10, _image.width + 10, 0, 0, _image.height * _scale, _image.width * _scale)
}

function redraw_all(_pages, _images, _canvases, _word_regions_by_page, _draw_word_confidence, _draw_ocr_text) {
    processed_pages.forEach(function (p, page_id) {
        draw_page(p, _images[page_id], _canvases[page_id], _word_regions_by_page[page_id], _draw_word_confidence, _draw_ocr_text)
    })
}
/*

function handle_correction(p) {
    // TODO
}

function import_saved_state(p) {
    // TODO
}
*/
function handle_page_clicks(click_x, click_y, _page_id, _page, _image, _canvas, _words) {
    _words.forEach(function (word) {
        //let block_id = word["block_id"];
        //let line_label = word["line_label"];
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
            get_image_slice(images[_page_id], x, y, w, h)
            draw_page(_page, _image, _canvas, _words, show_confidence, show_ocr, word);
            current_word = word;
        }
    })
}

// TODO: this doesn't really work. Probably a data structure problem
function next_word(_word, _pages, _images, _canvases, _words, _show_confidence, _show_ocr) {
    let _page_id = _word.page_id
    _words[_page_id].forEach(function (w, index) {
        if (_word == w) {
            // TODO: handle last word on page and last page
            current_word = _words[_page_id][index + 1]
            draw_page(_pages[_page_id], _images[_page_id], _canvases[_page_id], _words[_page_id], _show_confidence, _show_ocr, current_word);
        }
    })
}

const canvas_div = document.getElementById("canvas_div")
let canvases = {}
let images = {}
let scales = {}
let word_regions = {}

processed_pages.forEach(function (page, page_id) {
    canvases[page_id] = document.createElement("canvas");
    canvas_div.appendChild(canvases[page_id]);
    canvases[page_id].addEventListener('click', (e) => {
        var rect = e.target.getBoundingClientRect();
        var x = e.clientX - rect.left; //x position within the element.
        var y = e.clientY - rect.top;  //y position within the element.
        handle_page_clicks(x, y, page_id, page, images[page_id], canvases[page_id], word_regions[page_id])
    });
    images[page_id] = new Image();
    images[page_id].addEventListener("load", function () {
        canvases[page_id].width = images[page_id].width
        canvases[page_id].height = images[page_id].height
        scales[page_id] = images[page_id].width / page_images[page_id]['width']
        word_regions[page_id] = []
        Object.keys(page).forEach(function (block_id) {
            Object.keys(page[block_id]).forEach(function (line_label) {
                page[block_id][line_label].forEach(function (word) {
                    word_regions[page_id].push({
                        "page_id": page_id,
                        "block_id": block_id,
                        "line_label": line_label,
                        "word_confidence": word['wc'],
                        "word": word['word'],
                        "x": word['rect'][0] * scales[page_id],
                        "y": word['rect'][1] * scales[page_id],
                        "w": word['rect'][2] * scales[page_id],
                        "h": word['rect'][3] * scales[page_id],
                        'original_rect': word['rect']
                    })
                });
            });
        });
        draw_page(page, images[page_id], canvases[page_id], word_regions[page_id], show_confidence, show_ocr)
    });
    images[page_id].setAttribute("src", page_images[page_id]['url']);
});

document.getElementById("see_wc").addEventListener("change", function (event) {
    show_confidence = event.target.checked;
    redraw_all(processed_pages, images, canvases, word_regions, show_confidence, show_ocr)
});

document.getElementById("see_ocr").addEventListener("change", function (event) {
    show_ocr = event.target.checked;
    redraw_all(processed_pages, images, canvases, word_regions, show_confidence, show_ocr)
});

document.getElementById("next_word").addEventListener("click", function () {
    if (!current_word) {
        return
    }
    next_word(current_word, processed_pages, images, canvases, word_regions, show_confidence, show_ocr);
});