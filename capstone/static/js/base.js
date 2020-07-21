import 'bootstrap/js/dist/util'
import 'bootstrap/js/dist/collapse'
import 'bootstrap/js/dist/dropdown'
import 'bootstrap/js/dist/modal'

import $ from "jquery"
import * as utils from './utils.js'
import './analytics.js'

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
  $(burgericon).on('click touch', function(e) {
    $(body).toggleClass("hamburger-menu-open")
           .toggleClass("hamburger-menu-closed");
    e.stopPropagation();
  });
};

let selectedNavStyling = function() {
  let toolsPaths = ['bulk', 'api', 'search', 'search-docs', 'trends', 'trends-docs'];

  let path = window.location.pathname.split('/')[1];
  path = path.split('#')[0];

  let host = window.location.host.split('.')[0];

  if (host === 'cite' || toolsPaths.indexOf(path) > -1) {
    path = 'tools'
  } else if (path === 'user') {
    path = 'account'
  } else if (path === 'action') {
    path = 'courts'
  }

  $('#nav-' + path).find('a').addClass('selected');

};

let setupSidebarHighlighting = function () {
  let listGroup = $('.list-group-item');
  let subtitles = $('.subtitle');

  window.addEventListener('scroll', function() {
    for (let i=0; i<subtitles.length; i++) {
      if (utils.isScrolledIntoView(subtitles[i])){
        $(listGroup).removeClass('selected');
        let listGroupItem = "a.list-group-item[href='#" + subtitles[i].id + "']";
        $(listGroupItem).addClass('selected');
      }
    }
  })
};

let setupScrollStickiness = function() {
  const nav = $('#main-nav');
  const navHeight = nav.height();
  const halfNavHeight = navHeight/2;
  let stickOn = false;
  const contentDiv = document.getElementById('content-and-footer');
  const handleScroll = function() {
    if (contentDiv.scrollTop > halfNavHeight) {
      if (!stickOn) {
        nav.addClass("small-nav");
        stickOn = true;
      }
    } else {
      if (stickOn) {
        nav.removeClass("small-nav");
        stickOn = false;
      }
    }
  };
  contentDiv.addEventListener('scroll', handleScroll);
  handleScroll();  // handle case where page is already scrolled on load
};

$(function() {
  selectedNavStyling();
  setupScrollStickiness();
  setupSidebarHighlighting();
  setupDropdown();
  setupBurgerAction();
  patchAnchorTagButtons();
});
