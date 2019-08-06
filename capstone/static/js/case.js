import 'bootstrap/js/dist/tooltip'
import 'popper.js'

import Mark from 'mark.js';

let caseContainer = document.querySelector(".case-container");
let tooltip;

function getSearchPhrase() {
  // get highlight parameter
  const urlParams = new URLSearchParams(window.location.search);
  return urlParams.get('highlight');
}

let markInstance = new Mark(caseContainer);

function highlightSearchedPhrase() {
  // highlight all instances of parameter
  let keyword = getSearchPhrase();
  if (!keyword) return;
  let options = {
    separateWordSearch: false,
    diacritics: true,
    acrossElements: true
  };

  markInstance.mark(keyword, options);
}

caseContainer.addEventListener("mouseup", function () {

  let selection = window.getSelection();
  if (selection) {
    // console.log("want to highlight", selection.getRangeAt(0).toString(), "?");
    // debugger;
    addTooltip(selection)
  }

});


function addTooltip(selection) {
  if (tooltip) {
    tooltip.parentNode.removeChild(tooltip);
  }
  tooltip = document.createElement('a');
  tooltip.href = '#';
  tooltip.class = 'add-link-tooltip';
  tooltip.dataset.toggle = "tooltip";
  tooltip.dataset.placement = "top";
  tooltip.title = 'add link!';
  tooltip.innerText = "add link";
  selection.focusNode.parentNode.insertBefore(tooltip, selection.focusNode.nextSibling);
}

highlightSearchedPhrase();