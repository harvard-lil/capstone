import $ from 'jquery';
import Mark from 'mark.js';

let caseContainer = document.querySelector(".case-container");
let contextMenu = document.querySelector(".context-menu");
let selectedText = "";
let copiedSuccessfullyText = document.querySelector(".copied-successfully");

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

caseContainer.addEventListener("mouseup", function (event) {
  $(contextMenu).hide();
  let selection = window.getSelection();
  selectedText = selection.getRangeAt(0).toString();
  let encodedSelectedText = encodeURIComponent(selectedText);
  $("#search-google").attr("href", "https://www.google.com/search?hl=en&q=" + encodedSelectedText);
  $("#search-ddg").attr("href", "https://duckduckgo.com/?q=" + encodedSelectedText);
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
  // TODO: the following makes this feature accessible but it only works in Firefox
  // selection.focusNode.parentNode.appendChild(contextMenu);
}

function successCall() {
  $(copiedSuccessfullyText).show();
  setTimeout(()=>{
    $(contextMenu).hide();
    $(copiedSuccessfullyText).hide();
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