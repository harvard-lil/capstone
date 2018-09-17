// force link elements serving the role of buttons to respond correctly
let patchAnchorTagButtons = function () {
  document.querySelectorAll("a[role='button']").forEach(function(button){
    // activate when the spacebar is pressed; the browser should not scroll (default behavior)
    button.addEventListener('keypress', function(e){ if (e.key==' '||e.keyCode==32) { e.preventDefault(); this.click();}}, false);
    // when activated, don't navigate/re-focus/scroll the browser, change the location bar, or alter your browsing history
    button.addEventListener('click', function(e){ e.preventDefault(); }, false);
  })
}

let setupDropdown = function () {
    let dropdown = ".dropdown";
    $(dropdown).click(function(e) {
        let showingDropdown = $(this).hasClass("show");
        $(dropdown).removeClass("show");
        showingDropdown ? $(this).removeClass("show") : $(this).addClass("show");

        e.stopPropagation();
    });

    $(document).click(function(){
      $(dropdown).removeClass("show");
    });
};

let setupBurgerAction = function() {
  let body = 'body';
  let burgericon = '#burger-icon';
  /* start with closed hamburger */
  $(body).addClass('hamburger-menu-closed');
  $(burgericon).click(function() {
    $(body).toggleClass("hamburger-menu-open")
           .toggleClass("hamburger-menu-closed");
  });
};

let selectedNavStyling = function() {
  let path = window.location.pathname.split('/')[1];
  path = path.split('#')[0];
  path = path === 'user' ? 'account': path;
  path = path === 'bulk-access' || path === 'api' ? 'tools': path;
  $('#nav-' + path).find('a').addClass('selected');
};

$(function() {
  selectedNavStyling();
  setupDropdown();
  setupBurgerAction();
  patchAnchorTagButtons();
});
