<template>
  <div id="edit-app" :class="{darkMode}">
    <div id="app-grid" :class="{ showImage: showImage }">
      <header id="title">
        <h1><a :href="urls.case">{{templateVars.citation_full}}</a></h1>
      </header>

      <article id="caseTextPanel" :class="{scrollable: true, casePanel: true, hideConfidence: !showConfidence}" @click="handleWordClick">
        <CaseTextPanel :opinions="opinions"></CaseTextPanel>
      </article>
      <nav class="gutter gutter-vertical">‖</nav>
      <article v-if="showImage" id="caseImagePanel" :class="{scrollable: true, casePanel: true, hideConfidence: !showConfidence}" ref="pageImageContainer" @click="handleWordClick">
        <CaseImagePanel :pages="pages" :pngs="templateVars.pngs"></CaseImagePanel>
      </article>
      <nav id="view_controls">
        <button @click="darkMode=!darkMode" :class="{'toggle-btn': true, 'on': darkMode}">dark</button>
        <button @click="showImage=!showImage" :class="{'toggle-btn': true, 'on': showImage}">img</button>
        <button @click="$store.commit('toggleOcr')" :class="{'toggle-btn': true, 'on': showOcr}">OCR</button>
        <button @click="$store.commit('toggleConfidence')" :class="{'toggle-btn': true, 'on': showConfidence}">WC</button>
      </nav>
      <nav id="popups">
        <div :class="{ corrected: metadata.human_corrected }" id="human_corrected"
        title="'Human Corrected' means this case has been fully corrected and is essentially error-free. Set in the meta screen.">
          <div class="label">Human<br>Corrected</div>
        </div>
        <div id="edit_metadata">
          <button @click="toggleMetadata()" class="toggle-btn off">meta</button>
        </div>
        <div id="instructions">
          <button @click="toggleInstructions()" class="toggle-btn off">?</button>
        </div>
      </nav>
      <aside id="metadata">
        <MetadataPanel></MetadataPanel>
      </aside>
      <nav class="gutter gutter-horizontal">=</nav>
      <nav id="word">
        <EditPanel></EditPanel>
      </nav>
      <nav id="edits">
        <EditListPanel></EditListPanel>
      </nav>
      <nav id="document_controls">
        <button class="btn-primary" v-b-modal.save-modal>save to DB</button>
      </nav>
    </div>
    <b-modal id="save-modal" title="Save Changes" @ok="saveCase">
      <p>Permanently replace this case in the CAP database with your edited version?</p>
      <p>There is no undo for this command.</p>
      <form ref="saveForm" @submit.stop.prevent="saveCase">
        <b-form-group
          :state="saveFormValid"
          label="Description of your changes:"
          label-for="save-form-message"
          invalid-feedback="Description is required"
        >
          <b-form-input
            id="save-form-message"
            v-model="saveFormMessage"
            :state="saveFormValid"
            required
            autofocus
          ></b-form-input>
        </b-form-group>
        <span aria-live="polite">{{saveStatus}}</span>
      </form>
    </b-modal>
    <div v-if="showMetadata" class="pt-6 modal_overlay">
      <div class="col-8 offset-2 p-5 modal">
        <div class="modal_close" @click="toggleMetadata">&#8855;</div>
          <MetadataPanel></MetadataPanel>
      </div>
    </div>
    <div v-if="showInstructions" class="pt-6 modal_overlay">
      <div class="col-8 offset-2 p-5 modal">
        <div class="modal_close" @click="toggleInstructions">&#8855;</div>
        <h4>instructions</h4>
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
  import { mapState } from 'vuex';
  import Split from 'split-grid';

  import EditPanel from './edit-panel.vue'
  import EditListPanel from './edit-list-panel.vue'
  import CaseTextPanel from './case-text-panel.vue'
  import CaseImagePanel from './case-image-panel.vue'
  import MetadataPanel from './metadata-panel.vue'
  import {FAKE_SOFT_HYPHEN, SOFT_HYPHEN} from "./helpers";

  export default {
    components: {EditPanel, EditListPanel, CaseTextPanel, CaseImagePanel, MetadataPanel},
    computed: mapState(['showConfidence', 'showOcr', 'metadata', 'editedWords']),
    data() {
      return {
        pages: null,
        saveStatus: null,
        saveFormValid: null,
        saveFormMessage: '',
        showInstructions: false,
        showMetadata: false,
        showImage: true,
        darkMode: false,
        scrollLock: true,
        imagePanelOffset: null,
        scrollEventListeners: {},
      }
    },
    watch: {
      editedWords: {
        handler() {
          this.saveStateToStorage();
        },
        deep: true
      },
    },
    created() {
      // load local variables from Django template
      this.templateVars = templateVars;  // eslint-disable-line
      this.urls = this.templateVars.urls;
      this.opinions = this.templateVars.opinions;

      // preprocess metadata
      this.serverMetadata = this.templateVars.metadata;
      this.$store.commit('setMetadata', {...this.serverMetadata})

      // preprocess pages
      this.pages = this.templateVars.pages;
      this.blocksById = {};
      for (const page of this.pages)
        for (const block of page.blocks)
          this.blocksById[block.id] = block;

      // preprocess fonts
      this.fonts = this.templateVars.fonts;
      for (const fontId of Object.keys(this.fonts))
        this.fonts[fontId] = this.processFont(this.fonts[fontId]);
      this.fonts[-1] = {styles:'', family:'Times New Roman', size:12.0};  // default font
      this.charAscentCache = new Map();

      // load state from localStorage
      this.storageKey = `caseedit-${this.serverMetadata.id}`;
      const savedStateJson = localStorage.getItem(this.storageKey);
      this.savedWordEdits = {};
      if (savedStateJson) {
        try {
          const savedState = JSON.parse(savedStateJson);

          // for use in extracting words
          this.savedWordEdits = savedState.edit_list;

          // apply saved updates to metadata, if server val still matches old val
          if (Object.keys(savedState.metadata).length > 0) {
            for (const [k, [oldVal, newVal]] of Object.entries(savedState.metadata)) {
              if (this.serverMetadata[k] === oldVal)
                this.$store.commit('updateField', {path: `metadata.${k}`, value: newVal});
            }
          }
        } catch(e) {
          // localStorage is wiped in case of error, so bad state doesn't leave user with an unusable page
          console.log("Error applying edit_list to server state", e); // eslint-disable-line
          localStorage.removeItem(this.storageKey);
        }
      }
      this.extractWords();  // depends on saved state
    },
    mounted: function () {

      // document.addEventListener('keyup', (e)=>{
      //   if (e.ctrlKey) {
      //     switch(e.key) {
      //       case "o":
      //           this.showOcr = !this.showOcr;
      //         break;
      //       case "c":
      //         this.showConfidence = !this.showConfidence;
      //         break;
      //       case "s":
      //         this.saveCase();
      //         break;
      //       default:
      //         break;
      //     }
      //   }
      // });
      window.addEventListener('resize', ()=>{ this.handleWindowResize() });
      this.handleWindowResize();
      this.mounted = true;

      // grid resizing
      Split({
        columnGutters: [{
          track: 2,
          element: document.querySelector('.gutter-vertical'),
        }],
        rowGutters: [{
          track: 3,
          element: document.querySelector('.gutter-horizontal'),
        }],
        onDragEnd: this.handleWindowResize,
      });
    },
    methods: {
      handleWordClick(e) {
        if (!(e.target.classList.contains('word')))
          return;
        this.$store.commit('setCurrentWord', this.wordsById[e.target.dataset.id]);
      },
      wordConfidenceColor(word) {
        const alpha = (.6 - word.wordConfidence)*100;
        const red = 255 * word.wordConfidence + 127;
        return `rgba(${red}, 0, 0, ${alpha}%)`;
      },
      handleWindowResize() {
        this.$nextTick(() => {
          const containerWidth = this.$refs.pageImageContainer.offsetWidth;
          for (const page of this.pages) {
            this.$set(page, 'scale', containerWidth / page.width);
            // Conversion factor for font pts on scanned page to pixels.
            // For example, a font detected as "12pt" in our 300DPI scan was actually 12/72 * 300 == 50px high.
            page.fontScale = page.scale * 300 / 72;
          }
        });
      },
      extractWords() {
        /*
          Extract a list of words from the token stream in each page.blocks, and store the words in each page.words.

          word objects look like this: {
            blockId,
            wordConfidence, font,  // display metadata
            x, y, w, h,  // location
            lineHeight, yOffset,  // calculated OCR alignment values
            strings: [{index, value}],  // list of the original token stream strings composing this word
            originalString,  // merged strings, before any edits
            string,  // merged strings, including any edits
          }

          To save changes later, we'll update `blocks[blockId].tokens[index]` to `string`, and empty any additional `strings`.
         */
        let wordId = 0;
        const wordsById = this.wordsById = {};

        const startWord = (block, attrs, fontId, footnoteMark, page)=>{
          const rect = attrs.rect;
          return {
            blockId: block.id,
            wordConfidence: attrs.wc,
            font: this.fonts[fontId],
            strings: [],
            x: rect[0],
            y: rect[1],
            w: rect[2],
            h: rect[3],
            footnoteMark,
            page,
          };
        }

        const endWord = (word, words, wordEdits, fontId, block)=>{
          if (!word)
            return null;  // tag closed before opened -- shouldn't happen
          if (word.strings.length) {
            word.id = ++wordId;

            // apply saved edits, if any
            const wordIndex = words.length;
            word.index = wordIndex;
            word.originalString = word.strings.map(s=>s.value).join("").replace(SOFT_HYPHEN, FAKE_SOFT_HYPHEN);
            if (wordIndex in wordEdits && wordEdits[wordIndex][0] === word.originalString) {
              this.$store.commit('editWord', {word, string: wordEdits[wordIndex][1]});
            } else {
              word.string = word.originalString;
            }

            // for OCR alignment, calculate line height based on font, and apply a y offset based on the tallest
            // character in the word
            word.lineHeight = this.getFontLineHeight(fontId);
            word.yOffset = Math.min(...word.string.split('').map(c => word.lineHeight - this.getCharAscent(c, fontId)));

            // calculate background color
            word.wordConfidenceColor = this.wordConfidenceColor(word);

            words.push(word);
            block.words.push(word);
            wordsById[word.id] = word;
          }
          return null;
        }

        for (const page of this.pages) {
          const words = [];
          for (const block of page.blocks) {
            block.words = [];
            if (!block.tokens)
              continue;
            let word = null;
            let fontId = -1;
            let footnoteMark = false;
            let ocrAttrs = null;
            const wordEdits = this.savedWordEdits[page.id] && this.savedWordEdits[page.id][block.id] ? this.savedWordEdits[page.id][block.id] : {};
            for (const [i, token] of block.tokens.entries()) {
              if (typeof token === 'string') {
                if (word)
                  word.strings.push({index: i, value: token});
                continue;
              }
              const [tag, attrs] = token;
              if(tag === 'ocr') {
                ocrAttrs = attrs;
                word = startWord(block, attrs, fontId, footnoteMark, page);
              } else if(tag === '/ocr') {
                word = endWord(word, words, wordEdits, fontId, block);
              } else if(tag === 'font') {
                fontId = attrs.id;
              } else if(tag === '/font') {
                fontId = -1;
              } else if(tag === 'footnotemark') {
                // this doesn't currently accomplish anything, as footnoteMarks start and end inside ocr spans
                footnoteMark = true;
                word = endWord(word, words, wordEdits, fontId, block);
                word = startWord(block, ocrAttrs, fontId, footnoteMark, page);
              } else if(tag === '/footnotemark') {
                footnoteMark = false;
                word = endWord(word, words, wordEdits, fontId, block);
                word = startWord(block, ocrAttrs, fontId, footnoteMark, page);
              }
            }
          }
          page.words = words;
        }
      },
      toggleInstructions() {
        this.showInstructions = !this.showInstructions;
      },
      toggleMetadata() {
        this.showMetadata = !this.showMetadata;
      },
      async clearEdits() {
        if (!await this.$bvModal.msgBoxConfirm('Permanently discard your edits?\nThere is no undo for this command.')) {
          return;
        }
        localStorage.removeItem(this.storageKey);
        this.$store.commit('setMetadata', {...this.serverMetadata});
        for (const word of Object.values(this.$store.state.editedWords))
          this.$store.commit('editWord', {word, string: word.originalString});
      },
      getMetadataEdits() {
        /*
          Prepare dict of all edited metadata, including old value and new value so we can check for consistency
        */
        const metadata = {};
        for (const [k, v] of Object.entries(this.$store.state.metadata)) {
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
        for (const page of this.pages) {
          const pageId = page.id;
          for (const [wordIndex, word] of page.words.entries()) {
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
        if (!this.mounted)
          return;
        const save_state = this.getState(true)
        localStorage.setItem(this.storageKey, JSON.stringify(save_state));
      }, 500),
      async saveCase(event) {
        /* save to server */
        event.preventDefault();
        this.saveFormValid = this.$refs.saveForm.checkValidity();
        if (!this.saveFormValid)
          return;
        this.saveStatus = "saving ...";
        const state = this.getState();
        state.description = this.saveFormMessage;
        try {
          await $.ajax('', {
            type : 'POST',
            data: JSON.stringify(state),
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
        if (!this.charAscentCache.has(key)) {
          const canvas = document.createElement('canvas');
          const ctx = canvas.getContext('2d');
          const font = this.fonts[fontId];
          ctx.font = `${font.styles} ${font.size}pt ${font.family}`;
          // multiply by 3/4 to convert from px to pt
          this.charAscentCache.set(key, ctx.measureText(c).actualBoundingBoxAscent * 3/4);
        }
        return this.charAscentCache.get(key);
      },
      getFontLineHeight(fontId) {
        /*
          Return the ascent height of capital letters in this font.
          Setting a span's line-height: to this height means that capital letters will touch the top of the
          containing element, and we then only need to offset the span for lowercase letters.
        */
        return this.getCharAscent('T', fontId);
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
        let textStyles = [];
        if (font.style.includes('italics')) {
          styles.push('italic');
          textStyles.push('italic');
        }
        if (font.style.includes('smallcaps'))
          styles.push('small-caps');
        if (font.style.includes('bold'))
          styles.push('bold');
        return {
          family: `"${font.family}",${font.type}`,
          size: parseFloat(font.size),
          styles: styles.join(' '),
          textStyles: textStyles.join(' '),
        };
      },
    },
  }
</script>

<style lang="scss">
  .scrollable {
    border-left: 1px gray solid;
    padding: 1em;
  }
  .casePanel {
    padding: 0 2rem;
  }

  .current-word {
    border: 1px green solid !important;
  }
  .edited {
    border: 1px orange solid !important;
    &.current-word {
      outline: 1px green solid !important;
    }
  }
  .footnote-mark {
    vertical-align: super;
    font-size: .83em;
    background-color: #0000001f;
  }
  .hideConfidence .word {
    background-color: inherit !important;
  }

  .darkMode {
    article {
      border: thin solid gray;
    }
    div:not(#imageControls, .edit-word), h4{
      background-color: #2F2F2F;
      color: white;
    }
    img {
      filter: invert(1);
    }
    nav#edits .edited-word-list .edit-entry .edit-word {
      background-color: #232323;
    }
    nav#edits .edited-word-list .edit-head {
      background-color: #434343;
      .count_col, .clear_col {
         background-color: #434343;
      }
    }
    .footnote-mark {
      background-color: #ffffff1f;
    }
  }
</style>
