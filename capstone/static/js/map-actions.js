import {jurisdiction_translation} from './map-data.js'

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

  let statelinks = document.getElementsByClassName('state-link');

  Array.from(statelinks).forEach(function (element) {
    let jur_el = element.childNodes[1];
    let jurname = jur_el.id;
    add_event_to_jur('focus', element, jurname);
    add_event_to_jur('mouseover', jur_el, jurname);

  });
}

function add_event_to_jur(event, el, jurname) {
  // mapSettings lives in index.html, which calls this js file. eslint hates that.
  // eslint-disable-next-line
  const map_data = mapSettings.data;
  el.addEventListener(event, function () {
    Array.from(document.getElementsByClassName("jur_name")).forEach(function (el) {
      el.innerHTML = jurisdiction_translation[jurname]['name'];
    });

    Array.from(document.getElementsByClassName("num_cases")).forEach(function (el) {
      el.innerHTML =
          map_data[jurname]['case_count'].toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
    });
    Array.from(document.getElementsByClassName("num_reporters")).forEach(function (el) {
      el.innerHTML = map_data[jurname]['reporter_count'];
      // Pluralize "Reporters" text if there is more than one
      el.nextElementSibling.innerHTML = map_data[jurname]['reporter_count'] > 1 ? "Reporters" : "Reporter";
    });
    Array.from(document.getElementsByClassName("num_pages")).forEach(function (el) {
      el.innerHTML =
          map_data[jurname]['page_count'].toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
    });
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
        if (childID.indexOf('Dakota-Territory') > -1) {
          childID = 'Dakota-Territory'
        }
        el.setAttribute("href", mapSettings.jurisdictionUrl.replace("JURISDICTION", jurisdiction_translation[childID]['slug']));
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
