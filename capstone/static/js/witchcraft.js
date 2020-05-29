import $ from "jquery"
import { witchcraft_results } from './witchcraft-data.js'

let apiUrl = "https://api.case.law/v1";

let markupWithExtraInfo = function () {
  for (const jur in witchcraft_results) {
    let jurcases = witchcraft_results[jur];
    let jurtotal = 0;
    for (let i = 0; i < jurcases.length; i++) {
      if ("times_appeared" in jurcases[i]) {
        jurtotal += jurcases[i].times_appeared;
      }
    }
    jurcases.total_appearances = jurtotal;
    jurcases.total_cases = jurcases.length;
    jurcases.url = apiUrl + "/cases/?jurisdiction=" + jur + "&search=witchcraft";
  }
};

let showCase = function (jurname, info) {
  let jur_name_el = $(".jur_name");
  let jur_name_small_el = $(".jur_name_small");
  let num_cases_el = $(".num_cases");
  let num_appearances_el = $(".num_appearances");
  let api_list_link = $(".api-list-link");
  let excerpts = $(".excerpts");

  jur_name_el.text(jurname);
  jur_name_small_el.text(jurname);
  num_appearances_el.text(info.total_appearances);
  num_cases_el.text(info.total_cases);
  excerpts.empty();

  for (let i = 0; i < info.length; i++) {
    let excerpt_number = i + 1;
    let a_tag = "<a href='" + info[i].url + "'>" + info[i].name_abbreviation + "</a>";
    let decision_date = "<span class='excerpt-date'> " + info[i].decision_date + " </span>"
    excerpts.append("<p class='excerpt-item'>" +
        "<span class='excerpt-number'>" + excerpt_number + ") </span>" +
        "\"..." + info[i].context + "...\" " + a_tag + decision_date + "</p>")
  }
  api_list_link.attr("href", info.url);
};

let getRandomNum = function (min, max) {
  return Math.round(Math.random() * (max - min) + min);
};

let showRandomCase = function () {
  let allJurs = Object.keys(witchcraft_results);
  let randJur = allJurs[getRandomNum(0, allJurs.length)];
  const jurEl = $('#' + randJur);
  jurEl.addClass('state-selected');
  showCase(jurEl[0].ariaLabel, witchcraft_results[randJur]);
};

let setupEventsOnHover = function ($stateLink, jurname, info) {
  let selected_class = 'state-selected';
  $stateLink.on("click mouseover", function (e) {
    showCase(jurname, info);
    $('.state-link').removeClass(selected_class);
    $stateLink.addClass(selected_class);
    e.preventDefault();
  });

  // add focus events for users using tab
  $stateLink.parent().focus(function (e) {
    showCase(jurname, info);
    e.preventDefault();
  });
};

let setupClickEvent = function () {
  $('.state-link').click(function () {
    $('.state-link').off('mouseover');
  });
};

let parseWitchcraft = function () {
  for (const stateLink of $('.state-link')) {
    const slug = stateLink.id;
    if (slug in witchcraft_results) {
      //  assign results to map
      const $stateLink = $(stateLink);
      const new_opacity = witchcraft_results[slug].total_appearances / 45;
      $stateLink
          .css('fill', 'orange')
          .css('fill-opacity', new_opacity);
      setupEventsOnHover($stateLink, stateLink.ariaLabel, witchcraft_results[slug]);
    }
  }
};

$(function () {
  // hide difficult to represent jurisdictions for now
  $('#Dakota-Territory').hide();
  $('#US').hide();

  markupWithExtraInfo();
  parseWitchcraft();
  showRandomCase();
  setupClickEvent();
});