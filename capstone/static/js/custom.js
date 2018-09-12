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
});