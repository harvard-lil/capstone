<template>
  <div class="row grid-container">
    <div class="col-3 controls grid-item">
      <div class="sticky-top pt-5">
        <input type="checkbox" v-model="showOcr" id="show_ocr">
        <label for="show_ocr">OCR text</label>
        <br>
        <input type="checkbox" v-model="showConfidence" id="see_wc">
        <label for="see_wc">Word confidence</label>
        <div v-if="currentWord">
          <div
            :style="{
              'background-image':`url(${currentPage.page.image_url})`,
              'background-size': `${currentPage.page.width}px`,
              width: `${currentWord.w}px`,
              height: `${currentWord.h}px`,
              'background-position': `-${currentWord.x}px -${currentWord.y}px`,
            }"></div>
          <input type="text" id="current_word" v-model="currentWord.string" ref="currentWord">
          <small><small>
            (confidence: <span
            id="current_word_confidence">{{currentWord.word_confidence}}</span>)
          </small></small>
          <button @click="addSoftHyphen()">Add Soft Hyphen(⧟)</button>
        </div>
        <input type="text" v-model="metadata.name" placeholder="case name">
        <input type="text" v-model="metadata.docket_number" placeholder="docket number">
        <input type="text" v-model="metadata.decision_date_original" placeholder="decision date string">
        <button class="danger" @click="saveCase">Save Case To Database</button>
        <div>
          All changes are saved locally in your browser until you are ready to commit a batch of changes to the
          database.
        </div>
      </div>
    </div>
    <div id="canvas_div" class="col-9 grid-item">
      <page v-for="page in pages" :key="page.id" :page="page" :savedWordEdits="savedWordEdits[page.id]" ref="pageComponents"/>
    </div>
  </div>
</template>

<script>
  import $ from "jquery";
  import '../jquery_django_csrf';
  import debounce from "lodash.debounce";

  import Page from './page.vue'
  import {FAKE_SOFT_HYPHEN, SOFT_HYPHEN} from "./helpers";

  export default {
    components: {Page},
    data() {
      return {
        currentWord: null,
        currentPage: null,
        showOcr: true,
        showConfidence: true,
        metadata: null,
      }
    },
    watch: {
      metadata: {
        handler() {
          this.saveStateToStorage();
        },
        deep: true
      },
    },
    beforeMount: function () {
      // load local variables from Django template
      this.urls = templateVars.urls;  // eslint-disable-line
      this.metadata = templateVars.metadata;  // eslint-disable-line
      this.serverMetadata = {...this.metadata};
      this.pages = templateVars.pages;  // eslint-disable-line
      this.fonts = templateVars.fonts;  // eslint-disable-line

      // preprocess fonts
      for (const fontId of Object.keys(this.fonts))
        this.fonts[fontId] = this.processFont(this.fonts[fontId]);
      this.fonts[-1] = {styles:'', family:'Times New Roman', size:12.0};  // default font
      this.charAscentCache = {};

      // load state from localStorage
      this.storageKey = `caseedit-${this.metadata.id}`;
      this.savedWordEdits = {};
      const savedStateJson = localStorage.getItem(this.storageKey);
      if (savedStateJson) {
        try {
          const savedState = JSON.parse(savedStateJson);

          // for use in page rendering
          this.savedWordEdits = savedState.edit_list;

          // apply saved updates to metadata, if server val still matches old val
          if (Object.keys(savedState.metadata).length > 0) {
            for (const [k, [oldVal, newVal]] of Object.entries(savedState.metadata)) {
              if (this.metadata[k] === oldVal)
                this.metadata[k] = newVal;
            }
          }
        } catch(e) {
          // localStorage is wiped in case of error, so bad state doesn't leave user with an unusable page
          console.log("Error applying edit_list to server state", e);
          localStorage.removeItem(this.storageKey);
        }
      }
    },
    methods: {
      getMetadataEdits() {
        /*
          Prepare dict of all edited metadata, including old value and new value so we can check for consistency
        */
        const metadata = {};
        for (const [k, v] of Object.entries(this.metadata)) {
          const serverVal = this.serverMetadata[k];
          if (v !== serverVal)
            metadata[k] = [serverVal, v];
        }
        return metadata;
      },
      getTokenEdits(wordIndexed=false) {
        /*
          Prepare dict of all edited OCR strings, including old value and new value so we can check for consistency.
          Dict looks like {
            <pageId>: {
              <blockId>: {
                <index>: [oldVal, newVal]
              }
            }
          }
          With wordIndexed=false, <index> represents an index into the tokens for the block, used for saving to server.
          With wordIndexed=true, <index> represents index into clickable words in the block, used for saving to localStorage.
        */
        const editList = {};
        for (const pageComponent of this.$refs.pageComponents) {
          const pageId = pageComponent.page.id;
          for (const [wordIndex, word] of pageComponent.words.entries()) {
            if (word.string !== word.originalString) {
              if (!editList[pageId])
                editList[pageId] = {};
              if (!editList[pageId][word.blockId])
                editList[pageId][word.blockId] = {};
              if (wordIndexed) {
                editList[pageId][word.blockId][wordIndex] = [word.originalString, word.string];
              } else {
                const newString = word.string.replace(FAKE_SOFT_HYPHEN, SOFT_HYPHEN);
                for (const [i, string] of word.strings.entries()) {
                  editList[pageId][word.blockId][string.index] = [string.value, i === 0 ? newString : ''];
                }
              }
            }
          }
        }
        return editList;
      },
      getState(wordIndexed=false) {
        /* get state for saving to localStorage or server */
        return {
          'metadata': this.getMetadataEdits(),
          'edit_list': this.getTokenEdits(wordIndexed),
        };
      },
      saveStateToStorage: debounce(function() {
        /* save to local storage */
        localStorage.setItem(this.storageKey, JSON.stringify(this.getState(true)));
      }, 1000),
      async saveCase() {
        /* save to server */
        try {
          await $.ajax('', {
            type : 'POST',
            data: JSON.stringify(this.getState()),
            contentType: 'application/json',
          }).promise();
        } catch(e) {
          // TODO: show server error to user
          console.log("error saving:", e);
          return;
        }
        localStorage.removeItem(this.storageKey);
        window.location.href = this.urls.case;
      },
      getCharAscent(c, fontId) {
        /*
          Return character's ascent, meaning how high in pts the character visually reaches above the baseline in this font.
          (So "T" has a higher value than "i" has a higher value than "a", which is the same as "g".)
        */
        const key = `${fontId}-${c}`;
        if (!this.charAscentCache.hasOwnProperty(key)) {
          const canvas = document.createElement('canvas');
          const ctx = canvas.getContext('2d');
          const font = this.fonts[fontId];
          ctx.font = `${font.styles} ${font.size}pt ${font.family}`;
          // multiply by 3/4 to convert from px to pt
          this.charAscentCache[key] = ctx.measureText(c).actualBoundingBoxAscent * 3/4;
        }
        return this.charAscentCache[key];
      },
      getFontLineHeight(fontId) {
        /*
          Return the ascent height of capital letters in this font.
          Setting a span's line-height: to this height means that capital letters will touch the top of the
          containing element, and we then only need to offset the span for lowercase letters.
        */
        return this.getCharAscent('T', fontId);
      },
      addSoftHyphen() {
        document.execCommand('insertText', false, FAKE_SOFT_HYPHEN);
      },
      processFont(font) {
        /*
          Process backend font that looks like
            {type: "serif", style: "bold smallcaps", family: "Times New Roman", size: "11.00", width: "proportional"}
          into CSS-ready font snippets like
            {family: '"Times New Roman",serif', size: 11.0, styles: 'small-caps bold'}
          Snippets are kept separate so font size can be scaled later.
        */
        let styles = [];
        if (font.style.includes('italics'))
          styles.push('italic');
        if (font.style.includes('smallcaps'))
          styles.push('small-caps');
        if (font.style.includes('bold'))
          styles.push('bold');
        return {
          family: `"${font.family}",${font.type}`,
          size: parseFloat(font.size),
          styles: styles.join(' '),
        };
      },
    },
  }
</script>