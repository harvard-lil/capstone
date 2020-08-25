<template>
  <div id="edit-app">
    <div class="row p-2">
      <div class="col-6">
        <h1><a :href="urls.case">{{templateVars.citation_full}}</a></h1>
      </div>
      <div class="col-6 text-right viz-controls">
        <button @click="showOcr=!showOcr" :class="{'toggle-btn': true, 'on': showOcr}">(^O)CR</button>
        <button @click="showConfidence=!showConfidence" :class="{'toggle-btn': true, 'on': showConfidence}">W(^C)</button>
        <button @click="toggleInstructions" class="toggle-btn off">help</button>
        <button class="btn-primary mr-1 mb-1 ml-3" @click="saveCase($event)">(^s)ave case to DB</button>
        <button class="btn-secondary" @click="clearEdits">Clear All Edits</button>
        <span aria-live="polite"><span v-if="saveStatus" class="ml-1"><br>{{saveStatus}}</span></span>
      </div>
    </div>
    <div class="tools-row row">
      <div class="scrollable col-4">
        <h4 class="section-title">current word</h4>
        <div :style="currentWordStyle()"></div>
        <div class="row">
          <div class="col-10">
            <input type="text" id="current_word" :value="currentWord ? currentWord.string : ''" placeholder="current word" ref="currentWord" @input="wordEdited($event.target.value)">
          </div>
          <div class="col-2"><button @click="addSoftHyphen()" :disabled="currentWord === null">⧟</button></div>
        </div>
      </div>
      <div class="scrollable col-4 edits-container">
        <h4 class="section-title">edits</h4>
        <div class="edited-word-list mt-3">
          <div class="row edit-entry" v-for="word in editedWords" :key="word.id">
            <div class="col-5 word" @click="wordClicked(word)">{{word.originalString}}</div>
            <div class="col-6 word" @click="wordClicked(word)">{{word.string}}</div>
            <div class="col-1 edit-controls"><span class="edit-delete" @click="removeEdit(word.id)">&#8855;</span></div>
          </div>
        </div>
      </div>
      <div class="scrollable col-4">
        <h4 class="section-title">case metadata</h4>
        <div class="row">
          <label class="col-8 m-0" for="metadata-human-corrected">Human Corrected</label>
          <input class="col-4" type="checkbox" v-model="metadata.human_corrected" id="metadata-human-corrected">
          <small class="form-text text-muted">Set "Human Corrected" if this case has been fully corrected and is essentially error-free.</small>
          <label class="col-4" for="metadata-name-abbreviation">Short Name</label>
          <input class="col-8" type="text" v-model="metadata.name_abbreviation" placeholder="case short name" id="metadata-name-abbreviation">
          <label class="col-4" for="metadata-name">Long Name</label>
          <input class="col-8" type="text" v-model="metadata.name" placeholder="case name" id="metadata-name">
          <label class="col-4" for="metadata-decision-date-original">Decision Date (YYYY-MM-DD)</label>
          <input class="col-8" type="text" v-model="metadata.decision_date_original" placeholder="decision date" id="metadata-decision-date-original">
          <label class="col-4" for="metadata-docket-number">Docket Number</label>
          <input class="col-8" type="text" v-model="metadata.docket_number" placeholder="docket number" id="metadata-docket-number">
        </div>
      </div>
    </div>
    <div class="row" style="flex: 1 1 auto; overflow-y: auto;">
      <div id="textView" class="scrollable col-6">
        <div v-for="opinion in opinions" class="opinion">
          <h4 class="section-title">opinion: {{opinion.type}}</h4>
          <div v-for="paragraph in opinion.paragraphs" :key="paragraph.id" class="paragraph">
            <span class="paragraph-class">{{paragraph.class}}</span>
            <template v-for="block in paragraphBlocks(paragraph)"><span
              v-if="mounted"
              v-for="word in block.words"
              :key="word.id"
              :style="wordTextStyle(word)"
              @click="wordClicked(word)"
              :ref="`wordText${word.id}`"
              :class="wordClass(word)"
            >{{word.stringWithoutSoftHyphens}}</span></template>
          </div>

          <div v-if="opinion.footnotes && opinion.footnotes.length">
            <h4 class="section-title">{{opinion.type}} footnotes</h4>
            <div v-for="footnote in opinion.footnotes" :key="footnote.id">
              <span>{{footnote.label}}</span>

              <!-- THIS IS NOT DRY YET -- REPEAT OF ABOVE -->
              <div v-for="paragraph in footnote.paragraphs" :key="paragraph.id">
                <span class="paragraph-class">{{paragraph.class}}</span>
                <template v-for="block in paragraphBlocks(paragraph)"><span
                  v-if="mounted"
                  v-for="word in block.words"
                  :key="word.id"
                  :style="wordTextStyle(word)"
                  @click="wordClicked(word)"
                  :ref="`wordText${word.id}`"
                  :class="wordClass(word)"
                >{{word.stringWithoutSoftHyphens}}</span></template>
              </div>
              <!-- END THING TO DRY -->
            </div>
          </div>

        </div>
      </div>
      <div id="imageView" class="scrollable col-6" ref="pageImageContainer">
        <div v-for="page in pages" :key="page.id" ref="pageImages" :class="{page: true, 'show-ocr': showOcr}">
          <img :src="page.image_url" :width="page.width * page.scale" :height="page.height * page.scale">
          <span v-if="mounted"
                v-for="word in page.words"
                :key="word.id"
                :style="wordImageStyle(page, word)"
                @click="wordClicked(word)"
                :ref="`wordImage${word.id}`"
                :class="wordClass(word)">
            {{word.string}}
          </span>
        </div>
      </div>
    </div>
    <div class="pt-6" id="instructions_modal_overlay" style="display: none">
      <div class="col-8 offset-2 p-5" id="instructions_modal">
        <div id="modal_close" @click="toggleInstructions">&#8855;</div>
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
  import scrollIntoView from 'scroll-into-view-if-needed';

  import {FAKE_SOFT_HYPHEN, SOFT_HYPHEN} from "./helpers";

  export default {
    data() {
      return {
        pages: null,
        metadata: null,
        currentWord: null,
        showOcr: false,
        showConfidence: false,
        editedWords: {},
        saveStatus: null,
        mounted: false,
      }
    },
    watch: {
      metadata: {
        handler() {
          this.saveStateToStorage();
        },
        deep: true
      },
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
      this.metadata = this.templateVars.metadata;
      this.serverMetadata = {...this.metadata};

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
      this.charAscentCache = {};

      // load state from localStorage
      this.storageKey = `caseedit-${this.metadata.id}`;
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
      this.extractWords();  // depends on saved state
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
      for (const [i, page] of this.pages.entries())
        page.imageRef = this.$refs.pageImages[i];
      window.addEventListener('resize', ()=>{ this.handleWindowResize() });
      this.handleWindowResize();
      this.mounted = true;
    },
    methods: {
      wordEdited(newVal) {
        const word = this.currentWord;
        if (word.originalString === newVal)
          this.$delete(this.editedWords, word.id);
        else
          this.$set(this.editedWords, word.id, word);
        word.string = newVal;
        word.stringWithoutSoftHyphens = word.string.replace(FAKE_SOFT_HYPHEN, '');
      },
      paragraphBlocks(paragraph) {
        if (!paragraph.block_ids)
          return [];
        return paragraph.block_ids.map(blockId => this.blocksById[blockId]);
      },
      currentWordStyle() {
        if (this.currentWord) {
          const currentPage = this.pagesByWordId[this.currentWord.id];
          return {
            'background-image':`url(${currentPage.image_url})`,
            'background-size': `${currentPage.width}px`,
            width: `${this.currentWord.w}px`,
            height: `${this.currentWord.h}px`,
            'background-position': `-${this.currentWord.x}px -${this.currentWord.y}px`,
          };
        }
        return {width: '20rem', height: '2rem'};
      },
      wordImageStyle(page, word) {
        const font = word.font;
        return {
          left: `${word.x * page.scale}px`,
          top: `${word.y * page.scale - word.yOffset * page.fontScale - 1}px`,  // -1 for top border
          'background-color': this.showConfidence ? word.wordConfidenceColor : 'unset',
          // font format is "<styles> <font size>/<line height> <font families>":
          font: `${font.styles} ${font.size * page.fontScale}px/${word.lineHeight * page.fontScale}px ${font.family}`,
        };
      },
      wordTextStyle(word) {
        const font = word.font;
        return {
          'background-color': this.showConfidence ? word.wordConfidenceColor : 'unset',
          font: `${word.font.styles}`,
        };
      },
      wordClass(word) {
        return {
          'current-word': this.currentWord === word,
          'edited': word.string !== word.originalString,
          'footnote-mark': word.footnoteMark,
        };
      },
      wordClicked(word) {
        this.currentWord = word;
        this.$refs.currentWord.focus();
        this.scrollToWord(word.id);
      },
      wordConfidenceColor(word) {
        const alpha = (.6 - word.wordConfidence)*100;
        const red = 255 * word.wordConfidence + 127;
        return `rgba(${red}, 0, 0, ${alpha}%)`;
      },
      handleWindowResize() {
        const containerWidth = this.$refs.pageImageContainer.offsetWidth;
        for (const page of this.pages) {
          this.$set(page, 'scale', containerWidth / page.width);
          // Conversion factor for font pts on scanned page to pixels.
          // For example, a font detected as "12pt" in our 300DPI scan was actually 12/72 * 300 == 50px high.
          page.fontScale = page.scale * 300/72;
        }
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
        this.pagesByWordId = {};
        for (const page of this.pages) {
          const words = [];
          for (const block of page.blocks) {
            block.words = [];
            if (!block.tokens)
              continue;
            let word = null;
            let fontId = -1;
            let footnoteMark = false;
            const wordEdits = this.savedWordEdits[page.id] && this.savedWordEdits[page.id][block.id] ? this.savedWordEdits[page.id][block.id] : {};
            for (const [i, token] of block.tokens.entries()) {
              if (typeof token === 'string') {
                if (word)
                  word.strings.push({index: i, value: token});
                continue;
              }
              const [tag, attrs] = token;
              if(tag === 'ocr') {
                const rect = attrs.rect;
                word = {
                  blockId: block.id,
                  wordConfidence: attrs.wc,
                  font: this.fonts[fontId],
                  strings: [],
                  x: rect[0],
                  y: rect[1],
                  w: rect[2],
                  h: rect[3],
                  footnoteMark: footnoteMark,
                };
              } else if(tag === '/ocr') {
                if (!word)
                  continue;  // tag closed before opened -- shouldn't happen
                if (word.strings.length) {
                  // apply saved edits, if any
                  const wordIndex = words.length;
                  word.index = wordIndex;
                  word.originalString = word.strings.map(s=>s.value).join("").replace(SOFT_HYPHEN, FAKE_SOFT_HYPHEN);
                  if (wordIndex in wordEdits && wordEdits[wordIndex][0] === word.originalString) {
                    word.string = wordEdits[wordIndex][1];
                    this.editedWords[wordId] = word;
                  } else {
                    word.string = word.originalString;
                  }
                  word.stringWithoutSoftHyphens = word.string.replace(FAKE_SOFT_HYPHEN, '');

                  // for OCR alignment, calculate line height based on font, and apply a y offset based on the tallest
                  // character in the word
                  word.lineHeight = this.getFontLineHeight(fontId);
                  word.yOffset = Math.min(...word.string.split('').map(c => word.lineHeight - this.getCharAscent(c, fontId)));

                  // calculate background color
                  word.wordConfidenceColor = this.wordConfidenceColor(word);

                  wordId++;
                  word.id = wordId;
                  words.push(word);
                  block.words.push(word);
                  this.pagesByWordId[wordId] = page;
                }
                word = null;
              } else if(tag === 'font') {
                fontId = attrs.id;
              } else if(tag === '/font') {
                fontId = -1;
              } else if(tag === 'footnotemark') {
                // this doesn't currently accomplish anything, as footnoteMarks start and end inside ocr spans
                footnoteMark = true;
              } else if(tag === '/footnotemark') {
                footnoteMark = false;
              }
            }
          }
          page.words = words;
        }
      },
      toggleInstructions() {
        const instructions = document.getElementById("instructions_modal_overlay")
        instructions.style.display = instructions.style.display === "none" ? 'block' : 'none'
      },
      scrollToWord(wordId) {
        scrollIntoView(this.$refs[`wordText${wordId}`][0], {scrollMode: 'if-needed'});
        scrollIntoView(this.$refs[`wordImage${wordId}`][0], {scrollMode: 'if-needed'});
      },
      removeEdit(wordId) {
        const word = this.editedWords[wordId];
        word.string = word.originalString;
        this.$delete(this.editedWords, wordId);
      },
      clearEdits() {
        if (!confirm('CONFIRM: permanently discard your edits?\nThere is no undo for this command.')) {
          return;
        }
        localStorage.removeItem(this.storageKey);
        this.metadata = {...this.serverMetadata};
        for (const page of this.pages)
          for (const word of page.words)
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
        const save_state = this.getState(true)
        localStorage.setItem(this.storageKey, JSON.stringify(save_state));
      }, 500),
      async saveCase() {
        /* save to server */
        const description = prompt(`
          CONFIRM: permanently replace ${this.templateVars.citation_full} in the CAP database with your edited version?
          There is no undo for this command.
          Enter a description of your edits to continue:
        `, '');
        if (!description)
          return;
        this.saveStatus = "saving ...";
        const state = this.getState();
        state.description = description;
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

<style lang="scss" scoped>
  .scrollable {
    border: 2px gray solid;
    padding: 1em;
  }
  .page {
    position: relative;
    span {
      border: 1px transparent solid;
      line-height: 1;
      color: transparent;
      position: absolute;
    }
    &.show-ocr {
      img {
        opacity: 0.2;
      }

      span {
        color: unset;
      }
    }
  }
  .current-word {
    border: 1px green solid !important;
  }
  .edited {
    border: 1px orange solid !important;
  }
  #textView {
    padding: 2em;
    hyphens: none;
    .opinion {
      padding-bottom: 2em;
      padding-top: 2em;
      border-bottom: 1px gray solid;
    }
    .paragraph {
      margin-bottom: 1em;
    }
    .paragraph-class {
      margin-right: 1em;
      color: gray;
    }
    .footnote-mark {
      font-size: .83em;
      vertical-align: super;
    }
  }
</style>
