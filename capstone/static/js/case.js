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

function highlightSearchedWords() {
  let search = window.location.search;
  if (search.indexOf("highlight=") < 0) {
    return
  }
  let searchMatch = search.split("highlight=")[1];
  let highlighted = searchMatch.split("&")[0];
  let matched = decodeURI(highlighted);
  highlight(matched);
}


// from https://stackoverflow.com/a/29301739/2247227
function matchText (node, regex, callback, excludeElements) {
  /* This method iterates through all DOM nodes recursively
    and, if it finds a match, replaces the textNode with the original text,
    a span tag defined in the callback of matchText, and the rest of the original text */
  excludeElements || (excludeElements = ['script', 'style', 'iframe', 'canvas']);
  let child = node.firstChild;

  while (child) {
    switch (child.nodeType) {
      case 1:
        if (excludeElements.indexOf(child.tagName.toLowerCase()) > -1)
          break;
        matchText(child, regex, callback, excludeElements);
        break;
      case 3: {
        let bk = 0;
        child.data.replace(regex, function (all) {
          let args = [].slice.call(arguments);
          let offset = args[args.length - 2];
          let newTextNode = child.splitText(offset + bk);
          bk -= child.data.length + all.length;

          newTextNode.data = newTextNode.data.substr(all.length);
          let tag = callback.apply(window, [child].concat(args));
          child.parentNode.insertBefore(tag, newTextNode);
          child = newTextNode;
        });
        regex.lastIndex = 0;
        break;
      }
    }
    child = child.nextSibling;
  }
  return node;
}


function highlight(matchedTerm) {
  matchText(document.getElementsByClassName("casebody")[0], new RegExp(matchedTerm, "gi"), function (node, match) {
    let span = document.createElement("span");
    span.className = "highlight";
    span.textContent = match;
    return span;
  });
}

highlightSearchedWords();
