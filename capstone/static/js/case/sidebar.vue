<template>
  <div class="content">
    <div class="sidebar-section">
      <h2>Tools</h2>
    </div>
    <div v-if="opinions" class="sidebar-section outline">
      <h3>Case Outline</h3>
      <div class="sidebar-section-contents">
        <ul class="bullets">
          <li v-for="opinion in opinions">
            <a :href="`#${opinion.id}`">{{opinion.type}}</a>
            <span v-if="opinion.author"> — {{opinion.author}}</span>
          </li>
        </ul>
      </div>
    </div>
    <div class="sidebar-section">
      <h3>Other Formats</h3>
      <div class="sidebar-section-contents">
        <ul class="bullets">
          <li v-if="templateVars.urls.casePdf"><a :href="templateVars.urls.casePdf">PDF</a></li>
          <li><a :href="templateVars.urls.caseApi">API</a></li>
        </ul>
      </div>
    </div>
    <div class="sidebar-section">
      <h3>Selection Tools</h3>
      <div class="sidebar-section-contents">
        <ul class="bullets" v-if="selectedText">
          <li><a :href="linkToSelection()">Link to "{{selectedTextShort}}"</a></li>
          <li>
            <a href="#" @click.prevent="copyCiteToSelection">Copy "{{selectedTextShort}}" with cite</a>
            <span v-if="copyStatus">{{copyStatus}}</span>
          </li>
          <li><a :href="searchForSelection()">Search cases for "{{selectedTextShort}}"</a></li>
          <li v-if="templateVars.isStaff"><a href="#" @click.prevent="elideOrRedactSelection('elide')">⚠️ Elide "{{selectedTextShort}}"</a></li>
          <li v-if="templateVars.isStaff"><a href="#" @click.prevent="elideOrRedactSelection('redact')">⚠️ Redact "{{selectedTextShort}}"</a></li>
        </ul>
        <span v-else>Select text to link, cite, or search</span>
      </div>
    </div>
    <div  v-if="templateVars.isStaff" class="sidebar-section admin-tools">
      <h3>Admin Tools</h3>
      <div class="sidebar-section-contents">
        <ul class="bullets">
          <li><a :href="templateVars.urls.djangoAdmin">Django admin</a></li>
          <li><a :href="templateVars.urls.caseEditor">Case editor</a></li>
        </ul>
      </div>
    </div>
    <div class="sidebar-section explainer">
      <h3>What is this page?</h3>
      <div class="sidebar-section-contents">
        Every document on this site is part of the official caselaw of a court within the
        United States, scanned from the collection of the Harvard Law School Library. This is a
        {{ templateVars.jurisdictionName }} case from {{ templateVars.caseYear }}.
        <a :href="templateVars.urls.about">Learn more</a>.
      </div>
    </div>
  </div>
</template>

<script>
  import debounce from "lodash.debounce";
  import Mark from 'mark.js';
  import $ from "jquery";
  import '../jquery_django_csrf';

  export default {
    name: 'Sidebar',
    beforeMount: function () {
      this.templateVars = templateVars;  // eslint-disable-line
    },
    mounted() {
      // listen for text selections
      const caseContainer = document.querySelector('.case-container');
      document.addEventListener('selectionchange', debounce(() => {
        const selection = window.getSelection();
        if (!caseContainer.contains(selection.anchorNode))
          return;
        const selectedText = selection.getRangeAt(0).toString();
        if (selectedText) {
          this.selectedText = selectedText;
          this.lastSelection = selection;
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
        window.scrollTo({top: document.querySelector("mark").getBoundingClientRect().top - 100});
      }

      // handle keyboard controls
      document.addEventListener('keydown', (e) => {
        if ((e.ctrlKey || e.metaKey) && e.key === '/') {
          document.querySelector('#sidebar-menu').focus();
        } else if (e.key === 'Escape') {
          for (const previousNode of document.querySelectorAll('.focusable-element'))
            previousNode.remove();
          if (this.lastSelection) {
            const range = this.lastSelection.getRangeAt(0);
            range.insertNode(range.createContextualFragment("<span class='focusable-element' tabindex='-1'></span>"));
            document.querySelector('.focusable-element').focus();
          }
        }
      });

      // handle elisions
      function showOrHideElision(el) {
        const $el = $(el);
        if ($el.text() === $el.attr('data-hidden-text')) {
          $el.text($el.attr('data-orig-text'))
        }
        else {
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
          type: opinion.getAttribute('data-type').toLowerCase(),
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
      linkToSelection() {
        const url = new URL(window.location.href);
        url.searchParams.delete('highlight');
        url.searchParams.append('highlight', this.selectedText);
        return url.toString();
      },
      searchForSelection() {
        return templateVars.urls.search + "?search=" + encodeURIComponent(this.selectedText);
      },
      copyCiteToSelection() {
        // Copies: "Selected quotation" name_abbreviation, official_citation, (<year>)
        // TODO: add pin cite to citation
        const toCopy = "\"" + this.selectedText + "\" " + full_cite; // eslint-disable-line
        navigator.clipboard.writeText(toCopy).then(
          () => this.copyStatus = "done",
          () => this.copyStatus = "failed",
        );
      },
      elideOrRedactSelection(kind) {
        if(confirm(`Really ${kind} "${this.selectedText}"?`))
          $.post(templateVars.urls.redact, {'kind': kind, 'text': this.selectedText}, ()=>{window.location.reload()});
      },
    },
  }
</script>