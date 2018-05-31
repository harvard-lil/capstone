let resetChart = function() {
  // empty previous chart
  $(".chart-container")
      .empty()
      .html("<canvas id=\"caseChart\"></canvas>");
};

let populateJurisdictionData = function(data) {
  // on click in long jurisdiction list
  // show reporter, court, case totals
  $(".land").removeClass('active');
  let jur_svg = "#US-" + data.jurisdiction.slug;
  $(jur_svg).toggleClass('active');

  $('h5.selected-jurisdiction').text(data.jurisdiction.name_long);
  $('#court-count').text(formatNumToStr(data.court_count));
  $('#reporter-count').text(formatNumToStr(data.reporter_count.total));
  // $('#volume-count').text(formatNumToStr(reporter_count[id]['volume_count']));
  $('#case-count').text(formatNumToStr(data.case_count.total));
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
        label: 'Number of Cases',
        data: caseNumber,
        borderWidth: 1
      }],
    },

    options: {
      scales: {
        yAxes: [{
          ticks: {
            beginAtZero: true
          }
        }]
      }
    }
  });
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

let updateSelectedJurisdiction = function(id) {
    $.ajax({
    url: '?slug=' + id,
    success: function(data) {
      populateCaseChart(data.case_count.years);
      populateJurisdictionData(data);
      console.log('updating name', data.jurisdiction.name_long);
      $('#dropdown-menu-link').text(data.jurisdiction.name_long);
      window.ddata = data;
    }
  });
};


$(function() {
  // display Alabama first
  updateSelectedJurisdiction('ala');

  $("li.dropdown-item-text").on('click', function() {
    updateSelectedJurisdiction(this.id);
  });
});

