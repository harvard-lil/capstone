import $ from 'jquery';
import Mark from 'mark.js';
import debounce from 'lodash.debounce';

let caseContainer = document.querySelector(".case-container");
let contextMenu = document.querySelector(".context-menu");
let copiedSuccessfullyText = document.querySelector(".copied-successfully");
let selectedText, selection;


$(contextMenu).on('click', '#copy-url', (event) => {
  event.preventDefault();
  let updatedUrl = getUpdatedURL(selectedText);
  copyText(event, updatedUrl.href);
  successCall();
});

$(contextMenu).on('click', '#copy-text', (event) => {
  event.preventDefault();
  copyText(event, selectedText);
  successCall();
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
  $("#search-google").attr("href", "https://www.google.com/search?hl=en&q=" + encodedSelectedText);
  $("#search-ddg").attr("href", "https://duckduckgo.com/?q=" + encodedSelectedText);
  if (selectedText) {
    showContextMenu();
  }
}, 200));

function showContextMenu() {
  let selectedBoundingBox = selection.getRangeAt(0).getBoundingClientRect();
  $(contextMenu).css({
    left: selectedBoundingBox.x + (selectedBoundingBox.width / 2) + 'px',
    top: selectedBoundingBox.y + selectedBoundingBox.height + 'px'
  }).show();

  insertFocusableElement();
  $(selection.focusNode.nextElementSibling).before(contextMenu)

}

function contextMenuIsFocusedElement() {
  return document.activeElement.className.indexOf("context-menu") > -1;
}

function successCall() {
  $(copiedSuccessfullyText).show();
  setTimeout(()=>{
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
  let html = "<span class='focusable-element' tabindex='-1'></span>";
  if (selection.getRangeAt && selection.rangeCount) {
    let range = selection.getRangeAt(selection);
    let docFrag = range.createContextualFragment(html);
    range.insertNode(docFrag);
  } else if (document.selection && document.selection.createRange) {
    // IE < 9
    let range = document.selection.createRange();
    range.pasteHTML(html);
  }
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