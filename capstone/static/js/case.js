import Mark from 'mark.js';
// function copyCitation() {
//   /*
//      This bit of script selects the citation input and copies it. It then informs the users that the citation was copied
//      by applying the citation_copied class.
//    */
//   let citation_container = document.getElementById("citation_container");
//   let cite = document.getElementById("citation_for_copy");
//   cite.select();
//   document.execCommand("copy");
//   citation_container.classList.add("citation_copied");
// }

function getSearchPhrase() {
  // get highlight parameter
  const urlParams = new URLSearchParams(window.location.search);
  return urlParams.get('highlight');
}

let markInstance = new Mark(document.querySelector(".case-container"));

function highlightSearchedPhrase() {
  // highlight all instances of parameter
  let keyword = getSearchPhrase();
  let options = {
    separateWordSearch: false,
    diacritics: true,
    acrossElements: true
  };

  markInstance.mark(keyword, options);
}

highlightSearchedPhrase();