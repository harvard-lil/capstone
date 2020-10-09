<template>
    <div>
        <hr class="d-lg-none">
        <div v-if="opinions" class="sidebar-section outline" id="outline-section">
            <h2 class="sidebar-title">Case outline</h2>
            <div class="sidebar-section-contents">
                <ul>
                    <li v-for="opinion in opinions" :key="opinion.id">
                        <a  :href="`#${opinion.id}`">{{opinion.type}}</a>
                        <span v-if="opinion.author"> — {{opinion.author}}</span>
                    </li>
                </ul>
            </div>
        </div>
        <div class="sidebar-section" id="format-section">
            <h2 class="sidebar-title">Other formats</h2>
            <div class="sidebar-section-contents">
                <ul class="list-inline">
                    <li  class="list-inline-item" v-if="urls.casePdf"><a class="btn" :href="urls.casePdf">PDF</a></li>
                    <li class="list-inline-item" ><a class="btn" :href="urls.caseApi">API</a></li>
                </ul>
            </div>
        </div>
        <div class="sidebar-section" id="citing-section">
            <h2 class="sidebar-title">Citing cases</h2>
            <div class="sidebar-section-contents">
                <span v-if="citingCount === null"><a :href="urls.citedBy">cases citing to this case</a></span>
                <span v-else-if="citingCount === 0">No cases cite to this case</span>
                <span v-else>
                  <a :href="urls.citedBy">{{citingCount}} case{{citingCount===1?"":"s"}} cite to this case</a>
                </span>
            </div>
        </div>
        <hr class="d-none d-lg-block"/>
        <div class="sidebar-section d-none d-lg-block" id="tools-section">
            <h2 class="sidebar-title">Tools</h2>
            <h3>Selection tools</h3>
            <div class="sidebar-section-contents">
                <ul class="bullets" v-if="selectedText">
                    <li><a :href="linkToSelection()">Link to "{{selectedTextShort}}"</a></li>
                    <li>
                        <a href="#" @click.prevent="copyCiteToSelection">Copy "{{selectedTextShort}}" with cite</a>
                        <span aria-live="polite"><span v-if="copyStatus" class="ml-1">{{copyStatus}}</span></span>
                    </li>
                    <li><a :href="searchForSelection()">Search cases for "{{selectedTextShort}}"</a></li>
                    <li v-if="templateVars.isStaff"><a href="#" @click.prevent="elideOrRedactSelection('elide')">⚠️
                        Elide "{{selectedTextShort}}"</a></li>
                    <li v-if="templateVars.isStaff"><a href="#" @click.prevent="elideOrRedactSelection('redact')">⚠️
                        Redact "{{selectedTextShort}}"</a></li>
                </ul>
                <span v-else>Select text to link, cite, or search</span>
            </div>
        </div>
        <div class="sidebar-section d-none d-lg-block" id="analysis-section" v-if="Object.keys(templateVars.analysis).length">
            <h3>Analysis<a class="analysis-link" :href="`${urls.apiDocs}#analysis-fields`"><img class="analysis-info" alt="More information about analysis fields" :src="`${urls.static}img/icons/question.svg`"></a></h3>
            <div class="sidebar-section-contents">
                <ul>
                    <li v-if="templateVars.analysis.pagerank">PageRank: {{templateVars.analysis.pagerank}} </li>
                    <li v-if="templateVars.analysis.ocr_confidence">OCR confidence: {{templateVars.analysis.ocr_confidence}} </li>
                    <li v-if="templateVars.analysis.char_count">Character count: {{templateVars.analysis.char_count}} </li>
                    <li v-if="templateVars.analysis.word_count">Word count: {{templateVars.analysis.word_count}} </li>
                </ul>
            </div>
        </div>
        <div v-if="templateVars.isStaff || templateVars.canEdit" class="sidebar-section admin-tools" id="admin-section">
            <h3>Admin Tools</h3>
            <div class="sidebar-section-contents">
                <ul>
                    <li v-if="templateVars.isStaff"><a :href="urls.djangoAdmin">Django admin</a></li>
                    <li v-if="templateVars.canEdit"><a :href="urls.caseEditor">Case editor</a></li>
                </ul>
            </div>
        </div>
        <hr class="d-lg-flex"/>
        <div class="sidebar-section d-none d-lg-block" id="info-section">
            <h3>What is this page?</h3>
            <div class="sidebar-section-contents">
                Every document on this site is part of the official caselaw of a court within the
                United States, scanned from the collection of the Harvard Law School Library.
                <!-- This {{ templateVars.jurisdictionName }} case is from {{ templateVars.caseYear }}.-->
                <a :href="urls.about">Learn more</a>.
            </div>
        </div>
    </div>
</template>

<script>
  import debounce from "lodash.debounce";
  import Mark from 'mark.js';
  import $ from "jquery";
  import '../jquery_django_csrf';

  // this polyfill can be dropped if we're targeting Safari >= 13.1 and post-IE
  import * as clipboard from "clipboard-polyfill/dist/text/clipboard-polyfill.text.js";
  import {getApiUrl, jsonQuery} from "../api";

  export default {
    name: 'Sidebar',
    created() {
      this.templateVars = templateVars;  // eslint-disable-line
      this.urls = this.templateVars.urls;
      this.fetchCitingCount();
    },
    mounted() {
      // listen for text selections
      const caseContainer = document.querySelector('.case-container');
      document.addEventListener('selectionchange', debounce(() => {
        const selection = window.getSelection();
        if (!caseContainer.contains(selection.anchorNode))
          return;
        const selectedRange = selection.getRangeAt(0);
        const selectedText = selectedRange.toString();
        if (selectedText) {
          this.selectedText = selectedText;
          this.lastSelection = selectedRange;
        }
      }));
      // handle ?highlight= query param
      const highlightPhrase = new URLSearchParams(window.location.search).get('highlight');
      if (highlightPhrase) {
        const markInstance = new Mark(caseContainer);
        markInstance.mark(highlightPhrase, {
          separateWordSearch: false,
          diacritics: true,
          acrossElements: true
        });
        document.querySelector("mark").scrollIntoView();
        // document.getElementById('content-and-footer').scrollTo({top: document.querySelector("mark").getBoundingClientRect().top - 100});
      }

      // handle keyboard controls
      document.addEventListener('keydown', (e) => {
        if ((e.ctrlKey || e.metaKey) && e.key === '/') {
          document.querySelector('#sidebar-menu').focus();
        } else if (e.key === 'Escape') {
          for (const previousNode of document.querySelectorAll('.focusable-element'))
            previousNode.remove();
          if (this.lastSelection) {
            this.lastSelection.insertNode(this.lastSelection.createContextualFragment("<span class='focusable-element' tabindex='-1'></span>"));
            document.querySelector('.focusable-element').focus();
          }
        }
      });

      // handle elisions
      function showOrHideElision(el) {
        const $el = $(el);
        if ($el.text() === $el.attr('data-hidden-text')) {
          $el.text($el.attr('data-orig-text'))
        } else {
          $el.attr('data-orig-text', $el.text());
          $el.text($el.attr('data-hidden-text'));
        }
      }

      $(".elided-text").on('click', (evt) => {
        showOrHideElision(evt.target);
      }).on('keypress', (evt) => {
        if (evt.which === 13)
          showOrHideElision(evt.target);
      });

      // get opinions from case text
      const opinions = [];
      for (const opinion of caseContainer.querySelectorAll('.opinion')) {

        // get author name -- remove page numbers, strip non-word characters, lowercase
        let author = '';
        const authorEl = opinion.querySelector('.author');
        if (authorEl) {
          const $authorEl = $(authorEl).clone();
          $authorEl.find('.page-label').remove();
          author = $authorEl.text().toLowerCase().replace(/^[^\w.]|[^\w.]$/g, '');
        }

        opinions.push({
          id: opinion.firstElementChild.id,
          type: opinion.getAttribute('data-type').toLowerCase().replace('-', ' '),
          author: author,
        });
      }
      this.opinions = opinions;
    },
    data() {
      return {
        selectedText: null,
        lastSelection: null,
        copyStatus: null,
        opinions: null,
        citingCount: null,
        sidebarStatus: true,
      }
    },
    watch: {
      selectedText() {
        this.copyStatus = null;
      }
    },
    computed: {
      selectedTextShort() {
        const wordCount = 2;
        const words = this.selectedText.split(/\s+/);
        let out = words.slice(0, wordCount).join(" ");
        if (words.length > wordCount)
          out += " ...";
        return out;
      },
    },
    methods: {
      analysisValue(k, v) {
        if (k === "pagerank") {
          return `${(v.percentile * 100).toFixed(1)}%`;
        }
        return v.toLocaleString();
      },
      async fetchCitingCount() {
        const response = await jsonQuery(getApiUrl(this.urls.api, 'cases', {
          cites_to: this.templateVars.caseId,
          page_size: 1
        }));
        this.citingCount = response.count;
      },
      linkToSelection() {
        const url = new URL(window.location.href);
        url.searchParams.delete('highlight');
        url.searchParams.append('highlight', this.selectedText);
        return url.toString();
      },
      searchForSelection() {
        return this.urls.search + "?search=" + encodeURIComponent(this.selectedText);
      },
      copyCiteToSelection() {
        // Copies: "Selected quotation" name_abbreviation, official_citation, (<year>)
        // TODO: add pin cite to citation
        const toCopy = `"${this.selectedText}" ${this.templateVars.fullCite}`;
        clipboard.writeText(toCopy).then(
            () => this.copyStatus = "copied",
            () => this.copyStatus = "copy failed",
        );
      },
      elideOrRedactSelection(kind) {
        if (confirm(`Really ${kind} "${this.selectedText}"?`))
          $.post(this.urls.redact, {'kind': kind, 'text': this.selectedText}, () => {
            window.location.reload()
          });
      },
    },
  }
</script>