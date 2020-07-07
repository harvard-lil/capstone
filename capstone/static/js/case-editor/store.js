import Vuex from "vuex";
import Vue from "vue";


Vue.use(Vuex);
export default new Vuex.Store({
    state: {
        "word_regions": {},
        // eslint-disable-next-line
        "case_info": import_case_info_from_django_template,
        // eslint-disable-next-line
        "processed_pages": import_processed_pages_from_django_template,
        "show_confidence": true,
        "show_ocr": false,
        "current_word": {"word": null, "wc": null, "x": 0, "y": 0, "w": 0, "h": 0}
    },
    mutations: {
        set_current_word: (state, word) => {
            state.current_word = word;
        },
        toggle_show_ocr: (state) => { state.show_ocr = !state.show_ocr; },
        toggle_show_confidence: (state) => {  state.show_confidence = !state.show_confidence; },
        save_case: (state, q) => {
            state.case = q;
        },
        initialise_store(state) {
            let saved_words = localStorage.getItem('words');
            if (saved_words && saved_words.hasOwnProperty(state.case.id)) {
                state.word_regions = saved_words[state.case.id]
            } else {
                //TODO Load Shit
            }
        },
    },

});