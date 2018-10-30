let apiUrl = "https://api.case.law/v1";

let markupWithExtraInfo = function () {
  for (jur in witchcraft_results) {
    let jurcases = witchcraft_results[jur];
    let jurtotal = 0;
    for (let i = 0; i < jurcases.length; i++) {
      if ("times_appeared" in jurcases[i]) {
        jurtotal += jurcases[i].times_appeared;
      }
    }
    witchcraft_results[jur].total_appearances = jurtotal;
    witchcraft_results[jur].total_cases = jurcases.length;
    witchcraft_results[jur].url = apiUrl + "/cases/?jurisdiction=" + jur + "&search=witchcraft";
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
  for (jur in jurisdiction_translation) {
    if (jurisdiction_translation.hasOwnProperty(jur)) {
      if (jurisdiction_translation[jur].slug === randJur) {
        showCase(jurisdiction_translation[jur].name, witchcraft_results[randJur]);
        return
      }
    }
  }
};

let setupEventsOnHover = function (id, jurname, info) {
  let selected_class = 'state-selected';
  $(id).on("click mouseover", function (e) {
    showCase(jurname, info);
    $('.state').removeClass(selected_class);
    $(id).addClass(selected_class);
    e.preventDefault();
  });

  // add focus events for users using tab
  $(id).parent().focus(function (e) {
    showCase(jurname, info);
    e.preventDefault();
  });
};

let setupClickEvent = function () {
  $('.state').click(function (e) {
    $('.state').off('mouseover');
  });
};

let parseWitchcraft = function () {
  for (jur in jurisdiction_translation) {
    if (jurisdiction_translation.hasOwnProperty(jur)) {
      let slug = jurisdiction_translation[jur].slug;
      if (slug && slug in witchcraft_results) {
        //  assign results to map
        let jurid = "#" + jur;
        let new_opacity = witchcraft_results[slug].total_appearances / 100;
        $(jurid)
            .css('fill', 'orange')
            .css('fill-opacity', new_opacity);
        let jurname = jurisdiction_translation[jur].name;
        setupEventsOnHover(jurid, jurname, witchcraft_results[slug]);
      }
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