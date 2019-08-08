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
    addTooltip(selection, selectedText, 'copy URL')
    onTooltipSuccess(selection, selectedText)
  }
});

function createTooltip(rect, tooltipText) {
  let tt = document.createElement('a');
  tt.dataset.toggle = "tooltip";
  tt.title = tooltipText;
  tt.setAttribute('id', 'get-url-tooltip');
  tt.style.top = rect.top + 'px';
  tt.style.left = rect.left + 'px';
  tt.style.height = rect.height + 'px';

  // if width is larger than casebody width, assign it to casebody width
  let casebodyWidth = document.querySelector(".casebody").offsetWidth;
  tt.style.width = rect.width > casebodyWidth ? casebodyWidth + 'px' : rect.width + 'px';
  return tt;
}

function addTooltip(selection, selectedText, tooltipText, hideAfter) {
  let rect = window.getSelection().getRangeAt(0).getBoundingClientRect();
  let t = document.getElementById("url-for-copy");

  tooltip = createTooltip(rect, tooltipText);

  // add tooltip and textarea right after selected text node for a11y
  selection.focusNode.parentNode.appendChild(t);
  selection.focusNode.parentNode.appendChild(tooltip);

  // if selected text is at the top of the page, place tooltip at bottom of
  // selection so that it doesn't get lost in the nav bar
  let placement = rect.top < 100 ? 'bottom' : 'top';
  $(tooltip).tooltip({
    placement: placement,
    boundary: '.casebody',
    trigger: 'manual',
    container: selection.focusNode.parentNode
  }).tooltip('show');
  if (hideAfter) {
    setTimeout(function () {
      $(tooltip).tooltip('hide').remove()
    }, 800);
  }
}

function onTooltipSuccess(selection, selectedText) {
  // on tooltip div click, select text and update tooltip
  let createdtooltip_id = tooltip.attributes['aria-describedby'].value;
  let createdtooltip_el = document.getElementById(createdtooltip_id);

  createdtooltip_el.addEventListener('click', function (evt) {
    selectURLandHideTooltip(evt, selectedText);
    addTooltip(selection, selectedText, 'copied!', true)
  });
}

function selectURLandHideTooltip(evt, selectedText) {
  let t = document.getElementById("url-for-copy");
  let updatedUrl = getUpdatedURL(selectedText);
  t.value = updatedUrl.href;
  t.select();
  document.execCommand('copy');
  evt.preventDefault();
}

function getUpdatedURL(selectedText) {
  let url = new URL(window.location.href);
  url.searchParams.delete('highlight');
  url.searchParams.append('highlight', selectedText);
  return url
}

highlightSearchedPhrase();