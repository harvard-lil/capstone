<template>
  <div>
    <div id="metadata-box" class="row metadata">
      <div class="col-8 offset-3">
        <div class="row">
          <div class="col-6">
            <input type="text" v-model="metadata.name" placeholder="case name">
          </div>
          <div class="col-6">
            <input type="text" v-model="metadata.decision_date_original" placeholder="decision date string">
          </div>
        </div>
        <div class="row">
          <div class="col-6">
            <input type="text" v-model="metadata.docket_number" placeholder="docket number">
          </div>
        </div>
      </div>
    </div>
    <div class="row">
      <div class="col-3">
        <div class="sticky-top pt-5">
          <div class="row mt-5 mb-3" >
            <div  class="col">
              <div v-if="currentWord"
                :style="{
                  'background-image':`url(${currentPage.page.image_url})`,
                  'background-size': `${currentPage.page.width}px`,
                  width: `${currentWord.w}px`,
                  height: `${currentWord.h}px`,
                  'background-position': `-${currentWord.x}px -${currentWord.y}px`,
                }">&nbsp;</div>
              <div v-else :style="{ width: `20rem`, height: `2rem`}"></div>
            </div>
          </div>
          <div class="row">
            <div class="col-10">
              <input v-if="currentWord" type="text" id="current_word" v-model="currentWord.string" ref="currentWord">
              <input v-else type="text" disabled placeholder="current word">
            </div>
            <div class="col-2"><button @click="addSoftHyphen()" :disabled="currentWord === null">⧟</button></div>
          </div>
          <div class="row confidence">
            <div class="col-4">
              Confidence:
            </div>
            <div class="col-4">
               <span v-if="currentWord" id="current_word_confidence">{{currentWord.wordConfidence}}</span>
            </div>
          </div>
          <div class="edits-container row mt-5">
            <div class="col-6">
              <h4 class="edits-title">edits</h4>
            </div>
            <div class="save-button-box col-3">
              <button id="save_button" class="btn-secondary" @click="saveCase">(^s)ave</button>
            </div>
            <div class="save-button-box col-3">
              <button class="btn-secondary" @click="clearEdits">Clear</button>
            </div>
            <div class="row edited-word-list mt-3">
              <div class="col-12 ">
                <div v-for="(p, p_id) in savedWordEdits" :key="p_id">
                  <div v-for="(b, b_id) in p" :key="b_id">
                    <div>
                      <div class="row edit-entry" v-for="(w, i) in b" :key="i" >
                        <div class="col-5" @click="scrollToWord( b_id + '_' + w[1])">{{w[0]}}</div>
                        <div class="col-5" @click="scrollToWord( b_id + '_' + w[1])">{{w[1]}}</div>
                        <div class="col-2 edit-controls"><span class="edit-delete" @click="removeEdit(p, b_id, w, i)">&#8855;</span></div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
      <div id="canvas_div" class="col-8">
        <page v-for="page in pages" :key="page.id" :page="page" :savedWordEdits="savedWordEdits[page.id]" ref="pageComponents"/>
      </div>
      <div id="controls" class="col-1">
         <div class="sticky-top pt-6 mt-6 row">
           <div class="col viz-controls">
            <div class="row ocr-toggle" v-if="showOcr">
              <button v-on:click="showOcr=false" class="toggle-btn on">(^O)CR</button>
            </div>
            <div class="row ocr-toggle" v-else>
              <button v-on:click="showOcr=true" class="toggle-btn off">(^O)CR</button>
            </div>
            <div class="row wc-toggle" v-if="showConfidence">
              <button v-on:click="showConfidence=false" class="toggle-btn off">W(^C)</button>
            </div>
            <div class="row wc-toggle" v-else>
              <button v-on:click="showConfidence=true"  class="toggle-btn on">W(^C)</button>
            </div>
           </div>
          </div>
      </div>
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
    mounted: function () {

      const main_component = this;
      window.onkeyup = function(e){
        if ( e.ctrlKey ) {
          switch(e.key) {
            case "o":
                main_component.showOcr = !main_component.showOcr;
              break;
            case "c":
              main_component.showConfidence= !main_component.showConfidence;
              break;
            case "s":
              //main_component.savedWordEdits();
              main_component.saveCase();
              break;
            default:
              break;
          }
        }
      };
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
          console.log("Error applying edit_list to server state", e); // eslint-disable-line
          localStorage.removeItem(this.storageKey);
        }
      }
    },
    methods: {
      scrollToWord(scroll_string) {
        // Do we want to make this the current word? Is it possible that people might want to check other words they
        // while already editied they're editing a word? Possible but unlikely? Would people be more likely to want
        // to revisit a word they edited and make a change? It doesn't seem like it would be too confusing to have
        // the current word change if you clicked on it in this list.
        document.body.querySelector('span[scroll-to-here="' + scroll_string + '"]').scrollIntoView();
      },
      removeEdit(p, p_id, b_id, w) {
        p, p_id, b_id, w
        //TODO remove a single edit
      },
      clearEdits() {
        //TODO remove all the edits
      },
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
          alert("error saving:", e); // eslint-disable-line
          return;
        }
        this.saveAnimation();
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
        this.currentWord.string = this.currentWord.string + FAKE_SOFT_HYPHEN
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
      saveAnimation() {
        const save_box = document.getElementsByClassName('save-button-box')[0];
        const save_flash = setInterval(function(){
          save_box.classList.toggle('saving');
        }, 75);
        setTimeout(function () {
          clearInterval(save_flash)
          save_box.classList.remove('saving')
        }, 500)
      }
    },
  }
</script>