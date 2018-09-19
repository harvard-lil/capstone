// force link elements serving the role of buttons to respond correctly
let patchAnchorTagButtons = function () {
  document.querySelectorAll("a[role='button']").forEach(function(button){
    // activate when the spacebar is pressed; the browser should not scroll (default behavior)
    button.addEventListener('keypress', function(e){ if (e.key==' '||e.keyCode==32) { e.preventDefault(); this.click();}}, false);
    // when activated, don't navigate/re-focus/scroll the browser, change the location bar, or alter your browsing history
    button.addEventListener('click', function(e){ e.preventDefault(); }, false);
  })
}

const hideDropdown = function(dropdown) {
  dropdown.removeClass("show");
  dropdown.find("> a").attr("aria-expanded", "false");
};

const showDropdown = function(dropdown){
  dropdown.addClass("show");
  dropdown.find("> a").attr("aria-expanded", "true");
};

const setupDropdown = function () {
  const dropdowns = $(".dropdown");
  dropdowns.click(function(e) {
    const dropdown = $(this);
    const showingDropdown = dropdown.hasClass("show");
    hideDropdown(dropdowns);  // close other dropdowns
    showingDropdown ? hideDropdown(dropdown) : showDropdown(dropdown);
    e.stopPropagation();
  });

  $(document).click(function(){ hideDropdown(dropdowns) });
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
