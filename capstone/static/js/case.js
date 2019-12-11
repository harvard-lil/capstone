import $ from 'jquery';
import Mark from 'mark.js';
import debounce from 'lodash.debounce';

let caseContainer = document.querySelector(".case-container");
let contextMenu = document.querySelector(".context-menu");
let copiedSuccessfullyText = document.querySelector(".copied-successfully");
let elidedText = $(".elided-text");

let selectedText, selection;

$(contextMenu).on('click', '#copy-url', (event) => {
  event.preventDefault();
  let updatedUrl = getUpdatedURL(selectedText);
  copyText(event, updatedUrl.href);
  successCall();
});

$(contextMenu).on('click', '#copy-cite', (event) => {
  event.preventDefault();
  let formattedCitation = formatCitation();
  copyText(event, formattedCitation);
  successCall();
});

// This is a workaround: If there are other tab-able elements (like page labels, footnote markers, etc)
// tabbing will take user away from context menu and go straight to those elements
document.addEventListener('keydown', (event) => {
  if (event.keyCode === 9 && contextMenuIsShown() && !contextMenuIsFocusedElement()) {
    $('.context-menu').focus();
  }
});

document.addEventListener('selectionchange', debounce(() => {
  if (selectedText && contextMenuIsFocusedElement()) {
    // if menu is currently focused, don't close menu!
    return;
  }
  selection = window.getSelection();
  selectedText = selection.getRangeAt(0).toString();
  $(contextMenu).hide();
  // update search URLs
  let encodedSelectedText = encodeURIComponent(selectedText);

  $("#search-cap").attr("href", search_url + "?page=1&search=" + encodedSelectedText); // eslint-disable-line
  if (selectedText) {
    showContextMenu();
  }
}, 300));

// handle elisions
$(elidedText).on('click', (evt) => {
  if ($(evt.target).hasClass('shown')) {
    $(evt.target).find('.elision-help-text').hide();
    $(evt.target).text('...');
    $(evt.target).removeClass('shown')
  } else {
    $(evt.target).addClass('shown');
    $(evt.target).find('.elision-help-text').show();
    $(evt.target).text($(evt.target).attr('data-hidden-text'));
  }
});

function showContextMenu() {
  let selectedBoundingBox = selection.getRangeAt(0).getBoundingClientRect();
  insertFocusableElement();
  $(contextMenu).css({
    left: selectedBoundingBox.x + (selectedBoundingBox.width / 2) + 'px',
    top: selectedBoundingBox.y + selectedBoundingBox.height + 'px'
  }).show();
  $(selection.focusNode.parentNode).after(contextMenu);
}

function contextMenuIsFocusedElement() {
  return document.activeElement.className.indexOf("context-menu") > -1;
}

function contextMenuIsShown() {
  return $('.context-menu').is(":visible");
}

function successCall() {
  $(copiedSuccessfullyText).show();
  setTimeout(() => {
    $(contextMenu).hide();
    $(copiedSuccessfullyText).hide();
    $('.focusable-element').focus().remove();
  }, 1000);
}

function copyText(evt, textToCopy) {
  let t = document.getElementById("text-for-copy");
  t.value = textToCopy;
  t.select();
  document.execCommand('copy');
  evt.preventDefault()
}

function getUpdatedURL(selectedText) {
  let url = new URL(window.location.href);
  url.searchParams.delete('highlight');
  url.searchParams.append('highlight', selectedText);
  return url
}

function insertFocusableElement() {
  // After context menu is hidden, cursor should be on focusable element
  // Thanks to http://jsfiddle.net/hjfVw/

  // remove any existing elements
  $('.focusable-element').remove();

  let focusableElement = "<span class='focusable-element' tabindex='-1'></span>";
  if (selection.getRangeAt && selection.rangeCount) {
    let range = selection.getRangeAt(selection);
    let docFrag = range.createContextualFragment(focusableElement);
    range.insertNode(docFrag);
  } else if (document.selection && document.selection.createRange) {
    // IE < 9
    let range = document.selection.createRange();
    range.pasteHTML(focusableElement);
  }
}

function formatCitation() {
  // Returns: "Selected quotation" name_abbreviation, official_citation, (<year>)
  // TODO: add pin cite to citation
  return "\"" + selectedText + "\" " + full_cite; // eslint-disable-line
}


////// Find URL highlighted query in text

function getSearchPhrase() {
  // get highlight parameter
  const urlParams = new URLSearchParams(window.location.search);
  return urlParams.get('highlight');
}

let markInstance = new Mark(caseContainer);

function highlightSearchedPhrase(keyphrase) {
  // clear all previously highlighted
  markInstance.unmark();
  // highlight all instances of parameter
  keyphrase = keyphrase || getSearchPhrase();
  if (!keyphrase) return;
  let options = {
    separateWordSearch: false,
    diacritics: true,
    acrossElements: true
  };

  markInstance.mark(keyphrase, options);
  scrollToFirstHighlighted();
}

function scrollToFirstHighlighted() {
  let rect = document.querySelector("mark").getBoundingClientRect();
  window.scrollTo({top: rect.top - 100})
}

highlightSearchedPhrase();