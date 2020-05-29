/*
    Enable mouseover effects with the map on the homepage
 */

function addMapMouseovers() {
  let svgmap = document.getElementById("usa_territories_white");
  //This puts the original value of each count element in an attribute called data-original-value
  Array.from(document.getElementsByClassName("jur_name")).forEach(function (element) {
    set_original_value(element)
  });
  Array.from(document.getElementsByClassName("num_cases")).forEach(function (element) {
    set_original_value(element)
  });
  Array.from(document.getElementsByClassName("num_reporters")).forEach(function (element) {
    set_original_value(element)
  });
  Array.from(document.getElementsByClassName("num_pages")).forEach(function (element) {
    set_original_value(element)
  });

  //This sets the mouseout event for the map, which resets the count elements to their original value
  svgmap.addEventListener('mouseout', function () {
    Array.from(document.getElementsByClassName("jur_name")).forEach(function (element) {
      element.innerHTML = element.getAttribute("data-original-value")
    });
    Array.from(document.getElementsByClassName("num_cases")).forEach(function (element) {
      element.innerHTML = element.getAttribute("data-original-value")
    });
    Array.from(document.getElementsByClassName("num_reporters")).forEach(function (element) {
      element.innerHTML = element.getAttribute("data-original-value")
    });
    Array.from(document.getElementsByClassName("num_pages")).forEach(function (element) {
      element.innerHTML = element.getAttribute("data-original-value")
    })
  });

  svgmap.addEventListener('focusout', function () {
    Array.from(document.getElementsByClassName("jur_name")).forEach(function (element) {
      element.innerHTML = element.getAttribute("data-original-value")
    });
    Array.from(document.getElementsByClassName("num_cases")).forEach(function (element) {
      element.innerHTML = element.getAttribute("data-original-value")
    });
    Array.from(document.getElementsByClassName("num_reporters")).forEach(function (element) {
      element.innerHTML = element.getAttribute("data-original-value")
    });
    Array.from(document.getElementsByClassName("num_pages")).forEach(function (element) {
      element.innerHTML = element.getAttribute("data-original-value")
    })
  });

  // This loops through the elements of the map and sets the mouseover events
  for (const stateLink of document.getElementsByClassName('state-link')) {
    const jurPath = stateLink.childNodes[1];
    const jurSlug = stateLink.id;
    const jurName = stateLink.ariaLabel;
    add_event_to_jur('focus', stateLink, jurSlug, jurName);
    add_event_to_jur('mouseover', jurPath, jurSlug, jurName);
  }
}

function add_event_to_jur(event, el, jurSlug, jurName) {
  // mapSettings lives in index.html, which calls this js file. eslint hates that.
  // eslint-disable-next-line
  const map_data = mapSettings.data[jurSlug];
  el.addEventListener(event, function () {
    document.querySelector(".jur_name").innerHTML = jurName;
    document.querySelector(".num_cases").innerHTML = map_data['case_count'].toLocaleString();
    document.querySelector(".num_reporters").innerHTML = map_data['reporter_count'];
    document.querySelector(".num_reporters").nextElementSibling.innerHTML = map_data['reporter_count'] > 1 ? "Reporters" : "Reporter";
    document.querySelector(".num_pages").innerHTML = map_data['page_count'].toLocaleString();
  });
}

// Too dry? maybe.
function set_original_value(element) {
  const orig_attr = document.createAttribute("data-original-value");
  orig_attr.value = element.innerHTML;
  element.setAttributeNode(orig_attr);
}

function addJurHrefs() {
  let statelinks = document.getElementsByClassName('state-link');
  Array.from(statelinks).forEach(function (el) {
    Array.from(el.childNodes).forEach(function (child) {
      if (child.classList && child.classList.value.substring("state") !== -1) {
        // mapSettings lives in index.html, which calls this js file. eslint hates that.
        // eslint-disable-next-line
        let childID = child.id;
        if (childID.indexOf('dakota-territory') > -1) {
          childID = 'dakota-territory'
        }
        el.setAttribute("href", mapSettings.jurisdictionUrl.replace("JURISDICTION", childID));
        el.setAttribute("target", "_blank");
      }
    });
  });
}

/*
    got this code from:
    https://www.sitepoint.com/jquery-document-ready-plain-javascript/
 */

if (
    document.readyState === "complete" ||
    (document.readyState !== "loading" && !document.documentElement.doScroll)
) {
  addMapMouseovers();
  addJurHrefs();
} else {
  document.addEventListener("DOMContentLoaded", addMapMouseovers);
  document.addEventListener("DOMContentLoaded", addJurHrefs);
}
