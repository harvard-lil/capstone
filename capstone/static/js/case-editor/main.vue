<template>
  <div>
    <div id="metadata-box" class="row metadata">
      <div class="col-3">
        <button class="btn-primary mr-1 mb-1" @click="saveCase($event)">(^s)ave case to DB</button><br>
        <button class="btn-secondary" @click="clearEdits">Clear All Edits</button>
        <span aria-live="polite"><span v-if="saveStatus" class="ml-1"><br>{{saveStatus}}</span></span>
      </div>
      <div class="col-8">
        <div class="row">
          <div class="col-6">
              <div class="form-group">
                <label for="metadata-name-abbreviation">Short Name</label>
                <input type="text" v-model="metadata.name_abbreviation" placeholder="case short name" id="metadata-name-abbreviation">
              </div>
          </div>
          <div class="col-6">
              <div class="form-group">
                <label for="metadata-name">Long Name</label>
                <input type="text" v-model="metadata.name" placeholder="case name" id="metadata-name">
              </div>
          </div>
          <div class="col-6">
              <div class="form-group">
                <label for="metadata-decision-date-original">Decision Date (YYYY-MM-DD)</label>
                <input type="text" v-model="metadata.decision_date_original" placeholder="decision date" id="metadata-decision-date-original">
              </div>
          </div>
          <div class="col-6">
              <div class="form-group">
                <label for="metadata-docket-number">Docket Number</label>
                <input type="text" v-model="metadata.docket_number" placeholder="docket number" id="metadata-docket-number">
              </div>
          </div>
        </div>
      </div>
    </div>
    <div class="row">
      <div class="col-3 pl-3 pr-3">
        <div class="sticky-top pt-6">
          <div class="row mb-3" >
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
          <!--
          <div class="row confidence confidence_visual">
            <div class="col-4">
              Confidence:
            </div>
            <div class="col-4">
               <span v-if="currentWord" id="current_word_confidence">{{Math.round(currentWord.wordConfidence * 100)}}%</span>
            </div>
          </div>
          <div class="row">
            <div class="col">
               <span class="confidence-indicator" v-if="currentWord"
                :style="{'margin-left':`${currentWord.wordConfidence * 90}%`}">&#x29cd;</span>
            </div>
          </div>
          -->
          <div class="edits-container row mt-5">
            <div class="col-5 pt-1">
              <h4 class="edits-title">edits</h4>
            </div>
            <div class="row edited-word-list mt-3">
              <div class="col-12 ">
                <div v-for="(p, p_id) in savedWordEdits" :key="p_id">
                  <div v-for="(b, b_id) in p" :key="b_id">
                    <div>
                      <div class="row edit-entry" v-for="(w, w_id) in b" :key="w_id" >
                        <div class="col-5 word" @click="scrollToWord(p_id, b_id, w_id)">{{w[0]}}</div>
                        <div class="col-6 word" @click="scrollToWord(p_id, b_id, w_id)">{{w[1]}}</div>
                        <div class="col-1 edit-controls"><span class="edit-delete" @click="removeEdit(p_id, b_id, w_id)">&#8855;</span></div>
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
         <div class="sticky-top pt-6 row">
           <div class="col viz-controls">
            <div class="row ocr-toggle" v-if="showOcr">
              <button v-on:click="showOcr=false" class="toggle-btn on">(^O)CR</button>
            </div>
            <div class="row ocr-toggle" v-else>
              <button v-on:click="showOcr=true" class="toggle-btn off">(^O)CR</button>
            </div>
            <div class="row wc-toggle" v-if="showConfidence">
              <button v-on:click="showConfidence=false" class="toggle-btn on">W(^C)</button>
            </div>
            <div class="row wc-toggle" v-else>
              <button v-on:click="showConfidence=true"  class="toggle-btn off">W(^C)</button>
            </div>
            <div class="row instruction-toggle">
              <button v-on:click="toggleInstructions" class="toggle-btn off">help</button>
            </div>

           </div>
          </div>
      </div>
    </div>
    <div class="pt-6" id="instructions_modal_overlay" style="display: none">
      <div class="col-8 offset-2 p-5" id="instructions_modal">
        <div id="modal_close" v-on:click="toggleInstructions">&#8855;</div>
        <div class="row pt-3">
          <div class="q col-3">When should I press “Save”?</div>
          <div class="a col-9 pl-3">
            Corrections to a case should be made in a batch, and you should only press “save” when you have made all changes you intend to make to a case. This avoids preserving intermediate edits on the server that aren’t needed. In the meantime, each change you make will be immediately stored to your local browser storage, and will be stored across restarts until you are ready to save.
          </div>
        </div>
        <div class="row pt-3">
          <div class="q col-3">Why is there a space after each word?</div>
          <div class="a col-9 pl-3">
            The space after each word should be preserved (if it is supposed to be there) -- it controls whether there will be a space between that word and the next word when they are combined into text.
          </div>
        </div>
        <div class="row pt-3">
          <div class="q col-3">What is the significance of the word confidence labels?</div>
          <div class="a col-9 pl-3">
            The word confidence button highlights words that the OCR engine was less confident about. Word confidence is labeled by the OCR engine on a scale from 0.0 (least confident) to 1.0 (most confident). These scores have no objective meaning.
          </div>
        </div>
        <div class="row pt-3">
          <div class="q col-3">What is the “⧟” button for?</div>
          <div class="a col-9 pl-3">
            The “⧟” button is for inserting a “soft hyphen.” When the OCR engine sees a hyphen at the end of a line, it has to guess whether to encode the hyphen as a “hard hyphen,” which should be preserved in the text, or a “soft hyphen,” an invisible character which indicates where the word was broken over the line but should not be preserved in text.<br>
            For example, if the OCR engine saw “hyphen-” at the end of one line, and “ated” at the start of the next line, it needed to decide whether the text output should be “hyphen-ated” or “hyphenated.” If the engine wrongly output “hyphen-ated”, you could use the soft hyphen button to change it to “hyphen⧟” “ated”, which would render as “hyphenated” in the text.
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

  const toHashMap = (a,f) => a.reduce((a,c)=> (a[f(c)]=c,a),{});

  export default {
    components: {Page},
    data() {
      return {
        currentWord: null,
        currentPage: null,
        showOcr: true,
        showConfidence: true,
        metadata: null,
        savedWordEdits: {},
        saveStatus: null,
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
      this.pagesById = toHashMap(this.pages, p => p.id);
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
    mounted: function () {
      document.addEventListener('keyup', (e)=>{
        if (e.ctrlKey) {
          switch(e.key) {
            case "o":
                this.showOcr = !this.showOcr;
              break;
            case "c":
              this.showConfidence = !this.showConfidence;
              break;
            case "s":
              this.saveCase();
              break;
            default:
              break;
          }
        }
      });
      this.pageComponentsById = toHashMap(this.$refs.pageComponents, p => p.page.id);
    },
    methods: {
      toggleInstructions() {
        const instructions = document.getElementById("instructions_modal_overlay")
        instructions.style.display = instructions.style.display === "none" ? 'block' : 'none'
      },
      scrollToWord(p_id, b_id, w_id) {
        const pageComponent = this.pageComponentsById[parseInt(p_id)];
        pageComponent.wordClicked(pageComponent.words[w_id]);
        document.body.querySelector(`span[scroll-to-here="${b_id}_${w_id}"]`).scrollIntoView();
      },
      removeEdit(p_id, b_id, w_id) {
        const word = this.pageComponentsById[parseInt(p_id)].words[w_id];
        word.string = word.originalString;
      },
      clearEdits() {
        if (!confirm('CONFIRM: permanently discard your edits?\nThere is no undo for this command.')) {
          return;
        }
        localStorage.removeItem(this.storageKey);
        this.metadata = {...this.serverMetadata};
        for (const pageComponent of this.$refs.pageComponents)
          for (const word of pageComponent.words)
            if (word.string !== word.originalString)
              word.string = word.originalString;
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
        const save_state = this.getState(true)
        localStorage.setItem(this.storageKey, JSON.stringify(save_state));
        this.savedWordEdits = save_state['edit_list']
      }, 500),
      async saveCase() {
        /* save to server */
        if (!confirm('CONFIRM: permanently overwrite ' + this.metadata.name + ' in the CAP database with your edited ' +
                'version?\nThere is no undo for this command.')) {
          return;
        }
        this.saveStatus = "saving ...";
        try {
          await $.ajax('', {
            type : 'POST',
            data: JSON.stringify(this.getState()),
            contentType: 'application/json',
          }).promise();
        } catch(e) {
          this.saveStatus = `error saving: ${e}`;
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
    },
  }
</script>