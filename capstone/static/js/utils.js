/* helper function found in https://stackoverflow.com/questions/487073/check-if-element-is-visible-after-scrolling/488073#488073 */
function isScrolledIntoView(elem) {
  let offset = 200;
  let docViewTop = $(window).scrollTop();
  let docViewBottom = docViewTop + $(window).height();
  let elemTop = elem.offsetTop;
  let elemBottom = elemTop + $(elem).height();
  return ((elemBottom <= (docViewBottom - offset)) && (elemTop >= docViewTop));
}