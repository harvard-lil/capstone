import $ from 'jquery';
import 'popper.js'
import 'bootstrap/js/dist/tooltip'

import Mark from 'mark.js';

let caseContainer = document.querySelector(".case-container");
let tooltip;

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

caseContainer.addEventListener("mouseup", function () {
  $(tooltip).tooltip('hide').remove();
  let selection = window.getSelection();
  let selectedText = selection.getRangeAt(0).toString();
  if (selectedText) {
    addTooltip(selection, selectedText)
  }

});

function createTooltip(rect) {
  let tt = document.createElement('a');
  tt.dataset.toggle = "tooltip";
  tt.title = 'copy URL';
  tt.setAttribute('id', 'get-url-tooltip');
  tt.style.position = 'fixed';
  tt.style.top = rect.top + 'px';
  tt.style.left = rect.left + 'px';
  tt.style.height = rect.height + 'px';
  tt.style.width = rect.width + 'px';
  return tt;
}

function addTooltip(selection, selectedText) {
  let rect = window.getSelection().getRangeAt(0).getBoundingClientRect();
  let t = document.getElementById("url-for-copy");

  tooltip = createTooltip(rect);

  // add tooltip and textarea right after selected text node for a11y
  selection.focusNode.parentNode.insertBefore(tooltip, selection.focusNode.nextSibling);
  selection.focusNode.parentNode.insertBefore(t, selection.focusNode.nextSibling);
  $(tooltip).tooltip({placement: 'top', trigger: 'manual'}).tooltip('show');

  // on tooltip div click, select text and update tooltip
  let createdtooltip_id = tooltip.attributes['aria-describedby'].value;
  let createdtooltip_el = document.getElementById(createdtooltip_id);
  createdtooltip_el.addEventListener('click', function (evt) {
    selectURLandHideTooltip(evt, selectedText);
  });
}

function selectURLandHideTooltip(evt, selectedText) {
  let t = document.getElementById("url-for-copy");
  let updatedUrl = getUpdatedURL(selectedText);
  t.value = updatedUrl.href;
  t.select();
  document.execCommand('copy');
  evt.preventDefault();

  $(tooltip).attr('data-original-title', "copied!").tooltip('show');

  // hide tooltip after successful copy
  setTimeout(function () {
    $(tooltip).tooltip('hide')
  }, 800);
}

function getUpdatedURL(selectedText) {
  let url = new URL(window.location.href);
  url.searchParams.delete('highlight');
  url.searchParams.append('highlight', selectedText);
  return url
}

highlightSearchedPhrase();