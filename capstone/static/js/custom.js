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
  $(burgericon).click(function() {
    $(body).toggleClass("hamburger-menu-open")
           .toggleClass("hamburger-menu-closed");
  });
};

$(function() {
    setupDropdown();
    setupBurgerAction();
});