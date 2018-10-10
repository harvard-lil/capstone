/* helper function found in https://stackoverflow.com/questions/487073/check-if-element-is-visible-after-scrolling/488073#488073 */
function isScrolledIntoView(elem) {
  let docViewTop = $(window).scrollTop() - $('nav').height();

  /* checking if element is in the top half of the window */
  let docViewBottom = docViewTop + ($(window).height()/2);
  let elemBottom = elem.offsetTop + $(elem).height();
  let elemTop = elemBottom - $(elem).height();
  return ((elemBottom <= docViewBottom) && (elemTop >= docViewTop));
}