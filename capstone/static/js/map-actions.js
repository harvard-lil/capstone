import { jurisdiction_translation } from './map-data.js'

let apiUrl = "https://api.case.law/v1";

/*
    This bit of JS enables the mouseover effects with the map on the homepage
 */
let map_data = {
    "MH": {"page_count": 0, "reporter_count": 0, "case_count": 0},
    "PW": {"page_count": 0, "reporter_count": 0, "case_count": 0},
    "WF": {"page_count": 0, "reporter_count": 0, "case_count": 0},
    "FM": {"page_count": 0, "reporter_count": 0, "case_count": 0},
    "Regional": {"page_count": 8727621, "reporter_count": 19, "case_count": 2111123},
    "Dakota-Territory": {"page_count": 3368, "reporter_count": 1, "case_count": 310},
    "Native American": {"page_count": 11939, "reporter_count": 1, "case_count": 1951},
    "Navajo-Nation": {"page_count": 4387, "reporter_count": 1, "case_count": 695},
    "GU": {"page_count": 942, "reporter_count": 1, "case_count": 278},
    "US": {"page_count": 9547364, "reporter_count": 32, "case_count": 1693904},
    "MP": {"page_count": 6102, "reporter_count": 2, "case_count": 542},
    "PR": {"page_count": 323204, "reporter_count": 4, "case_count": 45488},
    "AS": {"page_count": 12978, "reporter_count": 3, "case_count": 2171},
    "VI": {"page_count": 51760, "reporter_count": 1, "case_count": 4042},
    "US-NV": {"page_count": 94834, "reporter_count": 1, "case_count": 11324},
    "US-DC": {"page_count": 192266, "reporter_count": 12, "case_count": 22510},
    "US-NC": {"page_count": 509994, "reporter_count": 23, "case_count": 96668},
    "US-NH": {"page_count": 128412, "reporter_count": 2, "case_count": 21241},
    "US-PA": {"page_count": 1238477, "reporter_count": 117, "case_count": 193459},
    "US-MT": {"page_count": 247616, "reporter_count": 1, "case_count": 27202},
    "US-IN": {"page_count": 350904, "reporter_count": 7, "case_count": 54984},
    "US-LA": {"page_count": 226605, "reporter_count": 13, "case_count": 59652},
    "US-WI": {"page_count": 546577, "reporter_count": 6, "case_count": 47222},
    "US-NJ": {"page_count": 735180, "reporter_count": 9, "case_count": 112581},
    "US-GA": {"page_count": 627815, "reporter_count": 9, "case_count": 169643},
    "US-SD": {"page_count": 65662, "reporter_count": 1, "case_count": 10118},
    "US-MA": {"page_count": 538673, "reporter_count": 23, "case_count": 90013},
    "US-MS": {"page_count": 250600, "reporter_count": 9, "case_count": 26534},
    "US-CA": {"page_count": 1357346, "reporter_count": 15, "case_count": 140822},
    "US-OK": {"page_count": 178132, "reporter_count": 3, "case_count": 41950},
    "US-ND": {"page_count": 63502, "reporter_count": 1, "case_count": 6467},
    "US-VT": {"page_count": 143460, "reporter_count": 6, "case_count": 21563},
    "US-AZ": {"page_count": 181994, "reporter_count": 2, "case_count": 28018},
    "US-WV": {"page_count": 222028, "reporter_count": 2, "case_count": 27526},
    "US-MI": {"page_count": 696445, "reporter_count": 12, "case_count": 78523},
    "US-UT": {"page_count": 96260, "reporter_count": 2, "case_count": 10076},
    "US-ID": {"page_count": 153620, "reporter_count": 1, "case_count": 18923},
    "US-WY": {"page_count": 47592, "reporter_count": 1, "case_count": 2736},
    "US-CO": {"page_count": 154343, "reporter_count": 4, "case_count": 23044},
    "US-NY": {"page_count": 2567177, "reporter_count": 83, "case_count": 1137735},
    "US-KY": {"page_count": 294753, "reporter_count": 16, "case_count": 55297},
    "US-KS": {"page_count": 345592, "reporter_count": 4, "case_count": 45690},
    "US-AK": {"page_count": 19328, "reporter_count": 2, "case_count": 2350},
    "US-FL": {"page_count": 168058, "reporter_count": 3, "case_count": 28041},
    "US-OR": {"page_count": 522308, "reporter_count": 3, "case_count": 55367},
    "US-TN": {"page_count": 238128, "reporter_count": 19, "case_count": 25898},
    "US-MD": {"page_count": 582928, "reporter_count": 10, "case_count": 42292},
    "US-IL": {"page_count": 1278142, "reporter_count": 10, "case_count": 183142},
    "US-OH": {"page_count": 713568, "reporter_count": 31, "case_count": 147692},
    "US-AL": {"page_count": 291964, "reporter_count": 6, "case_count": 77222},
    "US-SC": {"page_count": 312366, "reporter_count": 35, "case_count": 41555},
    "US-AR": {"page_count": 354839, "reporter_count": 3, "case_count": 55322},
    "US-RI": {"page_count": 89286, "reporter_count": 6, "case_count": 17537},
    "US-MN": {"page_count": 200976, "reporter_count": 1, "case_count": 34141},
    "US-NE": {"page_count": 282646, "reporter_count": 2, "case_count": 38478},
    "US-CT": {"page_count": 407332, "reporter_count": 9, "case_count": 54547},
    "US-ME": {"page_count": 99894, "reporter_count": 1, "case_count": 17218},
    "US-IA": {"page_count": 275202, "reporter_count": 4, "case_count": 40635},
    "US-TX": {"page_count": 310380, "reporter_count": 12, "case_count": 61537},
    "US-DE": {"page_count": 66196, "reporter_count": 8, "case_count": 8538},
    "US-MO": {"page_count": 526122, "reporter_count": 2, "case_count": 55303},
    "US-HI": {"page_count": 69798, "reporter_count": 4, "case_count": 8464},
    "US-NM": {"page_count": 130310, "reporter_count": 2, "case_count": 18338},
    "US-WA": {"page_count": 555498, "reporter_count": 4, "case_count": 101383},
    "US-VA": {"page_count": 379096, "reporter_count": 20, "case_count": 44692}
};


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

    Array.from(statelinks).forEach(function (element){
        let jur_el = element.childNodes[1];
        let jurname = jur_el.id;
        add_event_to_jur('focus', element, jurname);
        add_event_to_jur('mouseover', jur_el, jurname);

    });
}

function add_event_to_jur(event, el, jurname) {
    el.addEventListener(event, function () {
        Array.from(document.getElementsByClassName("jur_name")).forEach(function (el) {
            el.innerHTML = jurisdiction_translation[jurname]['name'];
        });

        Array.from(document.getElementsByClassName("num_cases")).forEach(function (el) {
            el.innerHTML =
                map_data[jurname]['case_count'].toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
        });
        Array.from(document.getElementsByClassName("num_reporters")).forEach(function (el) {
            el.innerHTML =
                map_data[jurname]['reporter_count']
            // Pluralize "Reporters" text if there is more than one
            el.nextElementSibling.innerHTML = map_data[jurname]['reporter_count'] > 1 ?  "Reporters" : "Reporter";
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
    Array.from(statelinks).forEach(function(el) {
        Array.from(el.childNodes).forEach(function(child) {
            if (child.classList && child.classList.value.substring("state") !== -1) {
               el.setAttribute("href", apiUrl + "/cases/?jurisdiction=" + jurisdiction_translation[child.id]['slug']);
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
