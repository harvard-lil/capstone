let apiURL = window.location.origin + '/api/v1/';
let resetChart = function() {
  // empty previous chart
  $(".chart-container")
      .empty()
      .html("<canvas id=\"caseChart\"></canvas>");
};

let populateJurisdictionData = function(data) {
  // on click in long jurisdiction list
  // show reporter, court, case totals

  // counts
  let court_count_el = $('#court-count');
  let reporter_count_el = $('#reporter-count');
  let case_count_el = $('#case-count');

  // firsts
  let first_reporter_el = $('#first-reporter');
  let first_case_el = $('#first-case');
  let first_year_el = $('#first-year');

  // show selected jurisdiction svg
  $(".land").removeClass('active');
  let jur_svg = "#US-" + data.jurisdiction.slug;
  $(jur_svg).toggleClass('active');

  // show selected jurisdiction name
  $('h5.selected-jurisdiction').text(data.jurisdiction.name_long);

  // add all counts
  court_count_el.text(formatNumToStr(data.court_count.total));
  reporter_count_el.text(formatNumToStr(data.reporter_count.total));
  // $('#volume-count').text(formatNumToStr(reporter_count[id]['volume_count']));
  case_count_el.text(formatNumToStr(data.case_count.total));

  // Fill in firsts
  first_year_el.text(Object.keys(data.case_count.years)[0]);

  // Add first case, direct to full case if it's whitelisted
  let link = apiURL + 'cases/' + data.case_count.firsts.id + '/';
  if (data.jurisdiction.whitelisted) {
    link += '?full_case=true';
  }

  first_case_el
      .text(abbreviateString(data.case_count.firsts.name_abbreviation))
      .attr('title', data.reporter_count.firsts.name)
      .attr('href', link);

  link = apiURL + 'reporters/' + data.reporter_count.firsts.id + '/';
  first_reporter_el
      .text(abbreviateString(data.reporter_count.firsts.name))
      .attr('title', data.reporter_count.firsts.name)
      .attr('href', link);
};


let populateStackedCaseChart = function () {
  let ctx = document.getElementById("caseChart").getContext('2d');
  let data = case_count_per_year;
  let datasets = [];
  for (let d in data) {
    datasets.push({
      data: data[d],
      label: '',
      backgroundColor: createRandomColor(),
      borderWidth: 1
      })
  }

  let chart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: data['years'],
      datasets: datasets,
    },
    options: {
        scales: {
            yAxes: [{
                stacked: true
            }],
           xAxes: [{
                stacked: true
            }]
        }
    }
  });
};

let createRandomColor = function() {
  let randVal = function() {
    return Math.floor(Math.random() * 255 + 1).toString();
  };
  return "rgba(" + randVal() + ", " + randVal() + ", " + randVal() + ", 0.5)"
};


let populateCaseChart = function (case_count) {
  let years = Object.keys(case_count);
  let caseNumber = Object.values(case_count);
  let ctx = document.getElementById("caseChart").getContext('2d');

  let chart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: years,
      datasets: [{
        label: 'Number of cases in',
        data: caseNumber,
        borderWidth: 0,
        fillColor: "rgba(216,216,216,1)",
      }],
    },

    options: {
      maintainAspectRatio: false,
      legend: {
        display: false
      },
      scales: {
        xAxes: [{
          gridLines: {
            display: false
          },
        }],
        yAxes: [{
          gridLines: {
            display: false
          },
          ticks: {
            stepSize: 1000
          }
        }]
      }
    }
  });
};

let abbreviateString = function(string) {
  if (string.length > 40) {
    return string.substr(0, 20) + "..." + string.substr(string.length - 10);
  } else {
    return string
  }
};

let formatNumToStr = function(num) {
  // takes a number, returns comma delineated string of that number
  if (!num || num === 0) return 0;
  let stringNum = num.toString();
  let newNumArray = [];
  let counter = 0;
  for (let i = stringNum.split('').length; i--;) {
    counter++;
    if (counter % 3 === 0 && i !== 0) {
      newNumArray.push(',' + stringNum[i]);
    } else {
      newNumArray.push(stringNum[i]);
    }
    if (i===0) {
      return newNumArray.reverse().join('');
    }
  }
};


let parseStrToNum = function(str) {
  // takes comma delineated str, returns num
  return parseInt(str.replace(/,/g, ''));
};

let updateSelectedJurisdiction = function(slug) {
    $.ajax({
    url: '/data/details/' + slug,
    success: function(data) {
      resetChart();
      populateCaseChart(data.case_count.years);
      populateJurisdictionData(data);
      $('#dropdown-menu-link').text(data.jurisdiction.name_long);
      $('#chosen-jurisdiction').text(data.jurisdiction.name_long);
      window.ddata = data;
    }
  });
};


$(function() {
  // if no jurisdiction is selected, display Illinois first
  let jurToDisplay = 'ill';
  if (window.location.search) {
    jurToDisplay = window.location.search.substr(1).split('slug=')[1];
  }
  updateSelectedJurisdiction(jurToDisplay);
});
