$(function() {
  $(".a-item").click(function() {
    let id = $(this).attr('id').split('jurisdiction-item-')[1];
    let slug, name;
    resetChart();

    if (id === 'totals') {
      slug = 'totals';
      name = 'Total'
      populateStackedCaseChart()
    } else {
      slug = jurisdiction_data[id].slug;
      name = jurisdiction_data[id].name_long;
      populateCaseChart(id);
    }
    populateJurisdictionData(this, name, id, slug);
  });

  // on load, display totals
  $('#jurisdiction-item-totals').click();
});

let resetChart = function() {
  // empty previous chart
  $(".chart-container")
      .empty()
      .html("<canvas id=\"caseChart\"></canvas>");
};

let populateJurisdictionData = function(el, name, id, slug) {
  // on click in long jurisdiction list
  // show reporter, court, case totals
  $(el).toggleClass('active');
  $(".land").removeClass('active');
  if (slug === 'totals') {
    $('#US-all').toggleClass('active');
  } else {
    $("#US-" + slug).toggleClass('active');
  }

  $('h5.selected-jurisdiction').text(name);
  if (id === 'totals') {
    $('#court-count').text(formatNumToStr(court_count['total']));
  } else {
    $('#court-count').text(formatNumToStr(court_count[id]));
  }

  if (id in reporter_count) {
    $('#reporter-count').text(formatNumToStr(reporter_count[id]['total']));
    $('#volume-count').text(formatNumToStr(reporter_count[id]['volume_count']));
  }
  if (id in case_count) {
    $('#case-count').text(formatNumToStr(case_count[id]['total']));
  }
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


let populateCaseChart = function (id) {
  if (!(id in case_count)) {
    return
  }

  let years = Object.keys(case_count[id]);
  let caseNumber = Object.values(case_count[id]);
  if (years[years.length-1] === 'total') {
    years.pop();
    caseNumber.pop();
  }
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
  if (!num) return
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