import $ from 'jquery';
import 'popper.js'
import 'bootstrap/js/dist/tooltip'

import Mark from 'mark.js';

let caseContainer = document.querySelector(".case-container");
let contextMenu = document.querySelector(".context-menu");
let selectedText = "";
let copiedSuccessfullyText = document.querySelector(".copied-successfully");
let copyURLBtn = document.getElementById("copy-url");
copyURLBtn.addEventListener("click", function (event) {
  event.preventDefault();
  let updatedUrl = getUpdatedURL(selectedText);
  copyText(event, updatedUrl.href);
  successCall();
});

let copyTextBtn = document.getElementById("copy-text");
copyTextBtn.addEventListener("click", function (event) {
  event.preventDefault();
  copyText(event, selectedText);
  successCall();
});

let copySearchGoogleBtn = document.getElementById("search-google");
let copySearchDDGBtn = document.getElementById("search-ddg");


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

caseContainer.addEventListener("mouseup", function (event) {
  $(contextMenu).hide();
  let selection = window.getSelection();
  selectedText = selection.getRangeAt(0).toString();
  let encodedSelectedText = encodeURIComponent(selectedText);
  $(copySearchGoogleBtn).attr("href", "https://www.google.com/search?hl=en&q=" + encodedSelectedText);
  $(copySearchDDGBtn).attr("href", "https://duckduckgo.com/?q=" + encodedSelectedText);
  let selectedBoundingBox = selection.getRangeAt(0).getBoundingClientRect();
  if (selectedText) {
    showContextMenu(selection, selectedBoundingBox, event);
  }
});

function showContextMenu(selection, selectedBoundingBox) {
  $(contextMenu).css({
    left: selectedBoundingBox.x + (selectedBoundingBox.width / 2) + 'px',
    top: selectedBoundingBox.y + selectedBoundingBox.height + 'px'
  }).show();
  selection.focusNode.parentNode.appendChild(contextMenu);
}

function successCall() {
  $(copiedSuccessfullyText).show();
  setTimeout(()=>{
    $(contextMenu).hide();
    $(copiedSuccessfullyText).hide();
  }, 1000);
}

function copyText(evt, textToCopy) {
  let t = document.getElementById("url-for-copy");
  evt.preventDefault();
  t.value = textToCopy;
  t.select();
  document.execCommand('copy');
}

function getUpdatedURL(selectedText) {
  let url = new URL(window.location.href);
  url.searchParams.delete('highlight');
  url.searchParams.append('highlight', selectedText);
  return url
}

highlightSearchedPhrase();