(function(e){function t(t){for(var a,i,n=t[0],o=t[1],c=t[2],d=0,h=[];d<n.length;d++)i=n[d],Object.prototype.hasOwnProperty.call(r,i)&&r[i]&&h.push(r[i][0]),r[i]=0;for(a in o)Object.prototype.hasOwnProperty.call(o,a)&&(e[a]=o[a]);u&&u(t);while(h.length)h.shift()();return l.push.apply(l,c||[]),s()}function s(){for(var e,t=0;t<l.length;t++){for(var s=l[t],a=!0,n=1;n<s.length;n++){var o=s[n];0!==r[o]&&(a=!1)}a&&(l.splice(t--,1),e=i(i.s=s[0]))}return e}var a={},r={search:0},l=[];function i(t){if(a[t])return a[t].exports;var s=a[t]={i:t,l:!1,exports:{}};return e[t].call(s.exports,s,s.exports,i),s.l=!0,s.exports}i.m=e,i.c=a,i.d=function(e,t,s){i.o(e,t)||Object.defineProperty(e,t,{enumerable:!0,get:s})},i.r=function(e){"undefined"!==typeof Symbol&&Symbol.toStringTag&&Object.defineProperty(e,Symbol.toStringTag,{value:"Module"}),Object.defineProperty(e,"__esModule",{value:!0})},i.t=function(e,t){if(1&t&&(e=i(e)),8&t)return e;if(4&t&&"object"===typeof e&&e&&e.__esModule)return e;var s=Object.create(null);if(i.r(s),Object.defineProperty(s,"default",{enumerable:!0,value:e}),2&t&&"string"!=typeof e)for(var a in e)i.d(s,a,function(t){return e[t]}.bind(null,a));return s},i.n=function(e){var t=e&&e.__esModule?function(){return e["default"]}:function(){return e};return i.d(t,"a",t),t},i.o=function(e,t){return Object.prototype.hasOwnProperty.call(e,t)},i.p="/static/dist/";var n=window["webpackJsonp"]=window["webpackJsonp"]||[],o=n.push.bind(n);n.push=t,n=n.slice();for(var c=0;c<n.length;c++)t(n[c]);var u=o;l.push([4,"chunk-common"]),s()})({"0629":function(e,t,s){"use strict";var a=s("e5f3"),r=s.n(a);t["default"]=r.a},"0838":function(e,t,s){"use strict";var a=s("08fb"),r=s("856f"),l=s("a6c2"),i=Object(l["a"])(r["default"],a["a"],a["b"],!1,null,null,null);t["default"]=i.exports},"08fb":function(e,t,s){"use strict";s.d(t,"a",(function(){return a})),s.d(t,"b",(function(){return r}));var a=function(){var e=this,t=e.$createElement,s=e._self._c||t;return s("li",{staticClass:"result"},[s("div",{staticClass:"result-title row"},[s("div",{staticClass:"col-md-9"},[s("a",{staticClass:"simple",attrs:{target:"_blank",href:e.$parent.metadata_view_url("jurisdiction",e.result.id)},domProps:{textContent:e._s(e.result.name_long)}})]),s("div",{staticClass:"col-md-3 decision-date"},[s("a",{staticClass:"see-cases",on:{click:function(t){return e.$parent.$emit("see-cases","jurisdiction",e.result.slug)}}},[e._v(" See cases ")])])])])},r=[]},"1cd0":function(e,t,s){"use strict";var a=s("f519"),r=s.n(a);t["default"]=r.a},"251f":function(e,t){e.exports={props:["result"]}},"2f77":function(e,t,s){"use strict";var a=s("e1b2"),r=s("0629"),l=s("a6c2"),i=Object(l["a"])(r["default"],a["a"],a["b"],!1,null,null,null);t["default"]=i.exports},"31b0":function(e,t,s){"use strict";var a=s("f789"),r=s("1cd0"),l=s("a6c2"),i=Object(l["a"])(r["default"],a["a"],a["b"],!1,null,null,null);t["default"]=i.exports},4:function(e,t,s){e.exports=s("9621")},"856f":function(e,t,s){"use strict";var a=s("251f"),r=s.n(a);t["default"]=r.a},9621:function(e,t,s){"use strict";s.r(t);var a=s("a4b5"),r=s("4af9"),l=function(){var e=this,t=e.$createElement,s=e._self._c||t;return s("div",{staticClass:"search-page"},[s("div",{staticClass:"row"},[s("search-form",{ref:"searchform",class:e.display_class,attrs:{field_errors:e.field_errors,search_error:e.search_error,endpoint:e.endpoint,fields:e.fields,query_url:e.query_url,choices:e.choices,urls:e.urls},on:{"new-search":e.newSearch,"update:endpoint":function(t){e.endpoint=t}}}),s("result-list",{class:e.display_class,attrs:{last_page:e.last_page,first_page:e.first_page,page:e.page,results:e.results,resultsType:e.resultsType,resultsShown:e.resultsShown,first_result_number:e.first_result_number,last_result_number:e.last_result_number,endpoint:e.endpoint,hitcount:e.hitcount,chosen_fields:e.chosen_fields,sort_field:e.sort_field,choices:e.choices,urls:e.urls},on:{"see-cases":e.seeCases,"next-page":e.nextPage,"prev-page":e.prevPage}})],1)])},i=[],n=(s("862d"),s("9588"),s("46d4"),s("fd85"),s("f1c6"),s("966c"),s("0ffc"),s("494a"),s("241c"),s("15db"),s("5a85"),s("dddc"),s("534d"),s("f432"),s("98ad")),o=s("57d2"),c=function(){var e=this,t=e.$createElement,s=e._self._c||t;return s("div",{staticClass:"search-form",attrs:{id:"sidebar-menu"}},[s("form",{staticClass:"row",on:{submit:function(t){return t.preventDefault(),e.$emit("new-search",e.fields,e.endpoint)}}},[s("div",{staticClass:"col-centered col-11"},[s("div",{staticClass:"col-md-2 empty-push-div"}),e._m(0),s("div",{staticClass:"row"},[s("div",{staticClass:"dropdown dropdown-search-routes"},[s("button",{staticClass:"btn dropdown-toggle dropdown-title",attrs:{type:"button",id:"search-routes-dropdown","data-toggle":"dropdown","aria-haspopup":"true","aria-expanded":"false","aria-describedby":e.endpoint}},[e._v(" "+e._s(e.endpoint)+" ")]),s("div",{staticClass:"dropdown-menu",attrs:{"aria-labelledby":"search-routes-dropdown"}},e._l(Object.keys(e.$parent.endpoints),(function(t){return s("a",{key:t,class:["dropdown-item","search-tab",t===e.endpoint?"active":""],on:{click:function(s){return e.changeEndpoint(t)}}},[e._v(" "+e._s(t)+" ")])})),0)])]),e.search_error?s("div",{staticClass:"alert alert-danger",attrs:{role:"alert"}},[s("p",[e._v(e._s(e.search_error))]),s("h2",{staticClass:"sr-only",attrs:{id:"form-errors-heading",tabindex:"-1"}},[e._v(" "+e._s(e.search_error)+" ")])]):e._e(),Object.keys(e.field_errors).length?s("div",{staticClass:"alert alert-danger",attrs:{role:"alert"}},[s("p",[e._v("Please correct the following "+e._s(Object.keys(e.field_errors).length)+" error(s):")]),s("h2",{staticClass:"sr-only",attrs:{id:"form-errors-heading",tabindex:"-1"}},[e._v(" Please correct the following "+e._s(Object.keys(e.field_errors).length)+" error(s)")]),s("ul",{staticClass:"bullets"},e._l(e.field_errors,(function(t,a){return s("li",{key:"error"+a},[s("a",{attrs:{href:"#"+a}},[e._v(e._s(e.getFieldByName(a).label)+":")]),e._v(" "+e._s(t)+" ")])})),0)]):e._e(),s("div",{staticClass:"search-fields row"},e._l(e.fields,(function(t){return s("div",{key:t.name,staticClass:"search-field",class:{"default-field":t.default,shown:e.advanced_fields_shown&&!t.default}},[t.default?[s("field-item",{attrs:{field:t,choices:e.choices[t.choices]}}),t.default&&e.field_errors[t.name]?s("div",{staticClass:"invalid-feedback"},[e._v(" "+e._s(e.field_errors[t.name])+" ")]):e._e(),t.default&&t.info?s("small",{staticClass:"form-text text-muted",attrs:{id:"help-text-"+t.name}},[e._v(" "+e._s(t.info)+" ")]):e._e()]:[e.advanced_fields_shown?[t.default?e._e():s("field-item",{key:t.name,attrs:{field:t,choices:e.choices[t.choices]}}),!t.default&&e.field_errors[t.name]?s("div",{staticClass:"invalid-feedback"},[e._v(" "+e._s(e.field_errors[t.name])+" ")]):e._e(),!t.default&&t.info?s("small",{staticClass:"form-text text-muted",attrs:{id:"help-text-"+t.name}},[e._v(" "+e._s(t.info)+" ")]):e._e()]:e._e()]],2)})),0),s("a",{staticClass:"btn btn-tertiary show-advanced-options",attrs:{href:"#","aria-label":"Show or hide advanced filters"},on:{click:function(t){e.advanced_fields_shown=!e.advanced_fields_shown}}},[e.advanced_fields_shown?s("span",[e._v("Hide advanced filters")]):s("span",[e._v("Show advanced filters")])]),s("div",{staticClass:"submit-button-group"},[s("search-button",{attrs:{showLoading:e.showLoading,endpoint:e.endpoint}}),e.show_explainer?s("a",{staticClass:"mt-0",attrs:{href:"#",id:"query-explainer-button"},on:{click:e.toggleExplainer}},[e._v("HIDE API CALL ")]):s("a",{staticClass:"mt-0",attrs:{href:"#",id:"query-explainer-button"},on:{click:e.toggleExplainer}},[e._v("SHOW API CALL")])],1),s("div",{directives:[{name:"show",rawName:"v-show",value:e.show_explainer,expression:"show_explainer"}],staticClass:"query-explainer"},[e._m(1),s("div",{staticClass:"row"},[s("div",{staticClass:"col-12 url-block"},[s("query-explainer",{attrs:{query_url:e.query_url}})],1)])]),s("div",{staticClass:"search-disclaimer"},[s("p",[e._v(" Searching U.S. caselaw published through mid-2018. "),s("a",{attrs:{href:e.urls.search_docs}},[e._v("Documentation")]),e._v("."),s("br")]),s("p",[s("span",{staticClass:"bold"},[e._v("Need legal advice?")]),e._v(" This is not your best option! Read about "),s("a",{attrs:{href:e.urls.search_docs+"#research"}},[e._v("our limitations and alternatives")]),e._v(". ")])])])])])},u=[function(){var e=this,t=e.$createElement,s=e._self._c||t;return s("div",{staticClass:"col-md-10 title-container"},[s("h3",{staticClass:"page-title"},[s("img",{staticClass:"decorative-arrow",attrs:{alt:"","aria-hidden":"true",src:"{% static 'img/arrows/violet-arrow-right.svg' %}"}}),e._v(" Search ")])])},function(){var e=this,t=e.$createElement,s=e._self._c||t;return s("div",{staticClass:"row"},[s("div",{staticClass:"col-12"},[s("small",{staticClass:"form-text text-muted",attrs:{id:"help-text-search"}},[e._v(" Hover over input boxes or url segments to expose their counterpart in your search query. ")])])])}],d=(s("2252"),s("15f7")),h=function(){var e=this,t=e.$createElement,s=e._self._c||t;return s("a",{staticClass:"text-break",attrs:{id:"query-explainer",href:e.query_url}},[s("span",[e._v(e._s(e.base_url))]),e._l(e.url_arguments,(function(t,a){return s("span",{key:a,staticClass:"api_url_segment",attrs:{id:e.argumentID(t)},on:{mouseenter:e.highlightQuery,mouseleave:e.unhighlightQuery},nativeOn:{focus:function(t){return e.alert("asd")}}},[0===a?[e._v("?")]:[e._v("&")],e._v(e._s(t))],2)}))],2)},f=[],p=(s("b902"),s("32ec"),s("6991"),{props:["query_url"],data:function(){return{url_arguments:[],base_url:""}},watch:{query_url:function(){this.update_string(this.query_url)}},methods:{update_string:function(e){var t=e.split("?");this.url_arguments=t[1].split("&"),this.base_url=t[0]},highlightQuery:function(e){var t=this.getInputBoxFromParameter(e.target.textContent);if(t&&!t.classList.contains("queryfield_highlighted")){var s=t.parentElement;t.classList.add("queryfield_highlighted"),s.classList.add("querylabel_highlighted")}},unhighlightQuery:function(e){var t=this.getInputBoxFromParameter(e.target.textContent);if(t&&t.classList.contains("queryfield_highlighted")){var s=t.parentElement;t.classList.remove("queryfield_highlighted"),s.classList.remove("querylabel_highlighted")}},getInputBoxFromParameter:function(e){var t=e.substring(1,e.indexOf("="));return document.getElementById(t)},argumentID:function(e){return"p_"+e.substring(0,e.indexOf("="))}}}),_=p,m=s("a6c2"),v=Object(m["a"])(_,h,f,!1,null,null,null),g=v.exports,b=function(){var e=this,t=e.$createElement,s=e._self._c||t;return e.field["choices"]?s("div",[s("div",{staticClass:"dropdown dropdown-field form-label-group"},[s("button",{staticClass:"btn dropdown-toggle dropdown-title",attrs:{type:"button",id:e.field.name,"data-toggle":"dropdown","aria-haspopup":"true","aria-expanded":"false","aria-describedby":e.field.label},on:{focus:e.highlightExplainer,blur:e.unhighlightExplainer}},[s("span",{staticClass:"dropdown-title-text"},[e._v(e._s(e.display_value))])]),s("div",{staticClass:"dropdown-menu",attrs:{"aria-labelledby":e.field.name}},e._l(e.choices,(function(t){return s("button",{key:t[0],class:["dropdown-item","search-tab",e.field.name===t[0]?"active":""],on:{click:function(s){return s.preventDefault(),e.updateDropdownVal(t)}}},[e._v(" "+e._s(t[1])+" ")])})),0)]),e.display_value===e.field.label||this.hide_reset?e._e():s("button",{staticClass:"dropdown-item reset-field",on:{click:function(t){return e.dropdownReset()}}},[s("small",[e._v("Reset "+e._s(e.field.label)+" field")])])]):"textarea"===e.field.type?s("textarea",{directives:[{name:"model",rawName:"v-model",value:e.field.value,expression:"field.value"}],staticClass:"form-control",class:["queryfield",e.$parent.field_errors[e.field.name]?"is-invalid":"","col-12"],attrs:{"aria-label":e.field.name,id:e.field["name"],placeholder:e.field["placeholder"]||!1},domProps:{value:e.field.value},on:{keyup:e.$parent.valueUpdated,focus:e.highlightExplainer,blur:e.unhighlightExplainer,input:function(t){t.target.composing||e.$set(e.field,"value",t.target.value)}}}):s("div",{staticClass:"form-label-group"},["checkbox"===e.field.type?s("input",{directives:[{name:"model",rawName:"v-model",value:e.field.value,expression:"field.value"}],class:["queryfield",e.$parent.field_errors[e.field.name]?"is-invalid":"","col-12"],attrs:{"aria-label":e.field.name,placeholder:e.field.label,id:e.field.name,min:e.field.min,max:e.field.max,type:"checkbox"},domProps:{checked:Array.isArray(e.field.value)?e._i(e.field.value,null)>-1:e.field.value},on:{input:e.$parent.valueUpdated,focus:e.highlightExplainer,blur:e.unhighlightExplainer,change:function(t){var s=e.field.value,a=t.target,r=!!a.checked;if(Array.isArray(s)){var l=null,i=e._i(s,l);a.checked?i<0&&e.$set(e.field,"value",s.concat([l])):i>-1&&e.$set(e.field,"value",s.slice(0,i).concat(s.slice(i+1)))}else e.$set(e.field,"value",r)}}}):"radio"===e.field.type?s("input",{directives:[{name:"model",rawName:"v-model",value:e.field.value,expression:"field.value"}],class:["queryfield",e.$parent.field_errors[e.field.name]?"is-invalid":"","col-12"],attrs:{"aria-label":e.field.name,placeholder:e.field.label,id:e.field.name,min:e.field.min,max:e.field.max,type:"radio"},domProps:{checked:e._q(e.field.value,null)},on:{input:e.$parent.valueUpdated,focus:e.highlightExplainer,blur:e.unhighlightExplainer,change:function(t){return e.$set(e.field,"value",null)}}}):s("input",{directives:[{name:"model",rawName:"v-model",value:e.field.value,expression:"field.value"}],class:["queryfield",e.$parent.field_errors[e.field.name]?"is-invalid":"","col-12"],attrs:{"aria-label":e.field.name,placeholder:e.field.label,id:e.field.name,min:e.field.min,max:e.field.max,type:e.field.type},domProps:{value:e.field.value},on:{input:[function(t){t.target.composing||e.$set(e.field,"value",t.target.value)},e.$parent.valueUpdated],focus:e.highlightExplainer,blur:e.unhighlightExplainer}}),s("label",{attrs:{for:e.field.name}},[e._v(" "+e._s(e.field.label)+" ")])])},y=[],w=new a["default"],C={name:"field-item",props:["field","hide_reset","choices"],data:function(){return{display_value:this.getFormattedDisplayValue()}},methods:{dropdownReset:function(){this.display_value=this.field.label,this.field.value=""},getFormattedDisplayValue:function(){var e=this;if(!this.choices)return"";var t=this.choices.filter((function(t){return e.field.value===t[0]}));return t[0]?this.field.label+": "+t[0][1]:this.field.label},updateDropdownVal:function(e){this.field.value=e[0],"ordering"!==this.field.name?this.display_value=this.getFormattedDisplayValue():this.$parent.updateOrdering()},highlightExplainer:function(e){var t=document.getElementById("p_"+e.target.id);t&&t.classList.add("highlight-parameter")},unhighlightExplainer:function(e){var t=document.getElementById("p_"+e.target.id);t&&t.classList.remove("highlight-parameter")}},mounted:function(){var e=this;w.$on("resetField",(function(t){t===e.field.name&&e.dropdownReset()}))}},x=C,k=Object(m["a"])(x,b,y,!1,null,null,null),S=k.exports,$={components:{FieldItem:S,SearchButton:d["a"],QueryExplainer:g},data:function(){return{query:[],show_explainer:!1,advanced_fields_shown:!1,defaultFields:[],otherFields:[]}},props:["search_error","field_errors","urls","showLoading","endpoint","fields","query_url","choices"],methods:{valueUpdated:function(){this.$parent.updateQueryURL()},getFieldByName:function(e){return this.$parent.endpoints[this.endpoint].find((function(t){return t.name===e}))},changeEndpoint:function(e){this.$emit("update:endpoint",e),this.valueUpdated()},toggleExplainer:function(){this.show_explainer=!this.show_explainer},downloadResults:function(e){return this.$parent.assembleUrl()+"&format="+e}},mounted:function(){this.valueUpdated()}},j=$,O=Object(m["a"])(j,c,u,!1,null,null,null),E=O.exports,q=function(){var e=this,t=e.$createElement,s=e._self._c||t;return e.showLoading?s("div",{staticClass:"results-loading-container"},[s("div",{staticClass:"row"},[s("div",{staticClass:"col-11 col-centered"},[s("img",{staticClass:"loading-gif",attrs:{alt:"","aria-hidden":"true",src:e.urls.static+"img/loading.gif"}}),s("div",{staticClass:"loading-text"},[e._v("Loading results...")])])])]):e.resultsShown?s("div",{staticClass:"results-list-container"},[s("div",{staticClass:"row"},[s("div",{staticClass:"col-11 col-centered"},[s("div",{staticClass:"row"},[s("ul",{staticClass:"col-9 list-inline field-choices"},[e._l(e.chosen_fields,(function(t){return[t.value?s("li",{key:t.name,staticClass:"list-inline-item field chosen-field"},[e._v(" "+e._s(t.label)+": "+e._s(t.value)+" "),s("span",{staticClass:"reset-field",on:{click:function(s){return e.reset_field(t.name)}}},[s("close-icon",{staticClass:"close-icon"})],1)]):e._e()]}))],2),"cases"===e.resultsType&&!e.toggle_download_options&&e.results[e.page]&&e.results[e.page].length?s("div",{staticClass:"col-3 download-options-trigger text-right"},[s("button",{staticClass:"btn btn-tertiary",on:{click:function(t){e.toggle_download_options=!e.toggle_download_options}}},[s("download-icon",{staticClass:"download-icon"}),s("br"),s("span",{staticClass:"small"},[e._v("download")])],1)]):e._e(),s("div",{staticClass:"col-12 download-options-container",class:e.toggle_download_options?"d-inline":"d-none"},[s("div",{staticClass:"row"},[e._m(0),s("div",{staticClass:"col-2 text-right"},[e.toggle_download_options?s("button",{staticClass:"btn btn-tertiary",on:{click:function(t){e.toggle_download_options=!e.toggle_download_options}}},[s("close-icon",{staticClass:"close-icon"})],1):e._e()])]),s("div",{staticClass:"row"},[s("div",{staticClass:"col-6 download-options"},[s("label",{attrs:{for:"max-downloads"}},[e._v("Max amount")]),s("input",{directives:[{name:"model",rawName:"v-model",value:e.local_page_size,expression:"local_page_size"}],attrs:{type:"number",id:"max-downloads",placeholder:e.local_page_size},domProps:{value:e.local_page_size},on:{input:function(t){t.target.composing||(e.local_page_size=t.target.value)}}}),s("label",{attrs:{for:"full-case"}},[e._v("Full case")]),s("input",{directives:[{name:"model",rawName:"v-model",value:e.full_case,expression:"full_case"}],attrs:{type:"checkbox",id:"full-case"},domProps:{checked:Array.isArray(e.full_case)?e._i(e.full_case,null)>-1:e.full_case},on:{change:function(t){var s=e.full_case,a=t.target,r=!!a.checked;if(Array.isArray(s)){var l=null,i=e._i(s,l);a.checked?i<0&&(e.full_case=s.concat([l])):i>-1&&(e.full_case=s.slice(0,i).concat(s.slice(i+1)))}else e.full_case=r}}})]),s("div",{staticClass:"col-6 text-right"},[s("div",{staticClass:"btn-group download-options row"},[s("div",{staticClass:"btn-group col-12"},[s("a",{staticClass:"btn-secondary download-formats-btn download-json",attrs:{target:"_blank",href:e.downloadResults("json"),title:"Download JSON"}},[e._v(" JSON ")]),e._v(" "),s("a",{staticClass:"btn-secondary download-formats-btn download-csv",attrs:{href:e.downloadResults("csv"),title:"Download CSV"}},[e._v(" CSV ")])])])])])])]),s("div",{staticClass:"row"},[s("div",{staticClass:"hitcount col-6",attrs:{id:"results_count_focus",tabindex:"-1"}},[e.results[e.page]&&e.results[e.page].length?s("span",{staticClass:"results-count"},[e._v(" "+e._s(e.first_result_number!==e.last_result_number?"Results "+e.first_result_number+" to "+e.last_result_number:"Result "+e.first_result_number)+" of "+e._s(e.hitcount?e.hitcount.toLocaleString():"many")+" ")]):s("span",{staticClass:"results-count"},[e._v("No results")])]),e.results[e.page]&&e.results[e.page].length?s("div",{staticClass:"col-6 text-right"},[s("field-item",{attrs:{field:e.sort_field,choices:e.choices[e.sort_field.choices],hide_reset:!0}})],1):e._e()]),"cases"===e.resultsType?s("ul",{staticClass:"results-list"},e._l(e.results[e.page],(function(e){return s("case-result",{key:e.id,attrs:{result:e}})})),1):"courts"===e.resultsType?s("ul",{staticClass:"results-list"},e._l(e.results[e.page],(function(e){return s("court-result",{key:e.id,attrs:{result:e}})})),1):"jurisdictions"===e.resultsType?s("ul",{staticClass:"results-list"},e._l(e.results[e.page],(function(e){return s("jurisdiction-result",{key:e.id,attrs:{result:e}})})),1):"reporters"===e.resultsType?s("ul",{staticClass:"results-list"},e._l(e.results[e.page],(function(e){return s("reporter-result",{key:e.id,attrs:{result:e}})})),1):e._e(),e.results[e.page]&&e.results[e.page].length?s("div",{staticClass:"row page-navigation-buttons"},[s("div",{staticClass:"col-6"},[!0!==e.first_page?s("button",{staticClass:"btn-secondary btn btn-sm",on:{click:function(t){return e.$emit("prev-page")}}},[e._v(" Back ")]):s("button",{staticClass:"btn-secondary btn btn-sm disabled",attrs:{disabled:""}},[e._v("Back")])]),s("div",{staticClass:"col-6 text-right"},[!0!==e.last_page?s("button",{staticClass:"btn-secondary btn btn-sm",on:{click:function(t){return e.$emit("next-page")}}},[e._v(" Page "+e._s(e.page+2)+" ")]):s("button",{staticClass:"btn-secondary btn btn-sm disabled",attrs:{disabled:""}},[e._v("Next")])])]):e._e()])])]):e._e()},P=[function(){var e=this,t=e.$createElement,s=e._self._c||t;return s("div",{staticClass:"col-10 download-title"},[s("strong",[e._v("Download options")])])}],F=(s("cbcf"),s("2f77")),L=s("6104"),R=s("31b0"),D=s("0838"),I=(s("c026"),s("2e1a")),T=s("755f"),N={functional:!0,render:function(e,t){var s=t._c,a=(t._v,t.data),r=t.children,l=void 0===r?[]:r,i=a.class,n=a.staticClass,o=a.style,c=a.staticStyle,u=a.attrs,d=void 0===u?{}:u,h=Object(T["a"])(a,["class","staticClass","style","staticStyle","attrs"]);return s("svg",Object(I["a"])({class:[i,n],style:[o,c],attrs:Object.assign({xmlns:"http://www.w3.org/2000/svg",height:"24",width:"24"},d)},h),l.concat([s("path",{attrs:{d:"M0 0h24v24H0V0z",fill:"none"}}),s("path",{attrs:{d:"M18.3 5.71a.996.996 0 00-1.41 0L12 10.59 7.11 5.7A.996.996 0 105.7 7.11L10.59 12 5.7 16.89a.996.996 0 101.41 1.41L12 13.41l4.89 4.89a.996.996 0 101.41-1.41L13.41 12l4.89-4.89c.38-.38.38-1.02 0-1.4z"}})]))}},U={functional:!0,render:function(e,t){var s=t._c,a=(t._v,t.data),r=t.children,l=void 0===r?[]:r,i=a.class,n=a.staticClass,o=a.style,c=a.staticStyle,u=a.attrs,d=void 0===u?{}:u,h=Object(T["a"])(a,["class","staticClass","style","staticStyle","attrs"]);return s("svg",Object(I["a"])({class:["feather feather-download",i,n],style:[o,c],attrs:Object.assign({xmlns:"http://www.w3.org/2000/svg",width:"24",height:"24",fill:"none",stroke:"currentColor","stroke-width":"2","stroke-linejoin":"round"},d)},h),l.concat([s("path",{attrs:{d:"M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M7 10l5 5 5-5M12 15V3"}})]))}},M={props:["results","first_result_number","last_result_number","showLoading","resultsShown","resultsType","endpoint","hitcount","chosen_fields","page","first_page","last_page","urls","sort_field","choices"],data:function(){return{local_page_size:1e4,full_case:!1,selected_fields:[],toggle_download_options:!1}},components:{ReporterResult:F["default"],CaseResult:L["default"],CourtResult:R["default"],JurisdictionResult:D["default"],CloseIcon:N,DownloadIcon:U,FieldItem:S},methods:{metadata_view_url:function(e,t){return this.urls.view_court.replace("987654321",t).replace("/court/","/"+e+"/")},reset_field:function(e){w.$emit("resetField",e)},downloadResults:function(e){var t="";return this.full_case&&(t="&full_case=true"),this.$parent.assembleUrl(this.local_page_size)+"&format="+e+t},updateOrdering:function(){this.$parent.assembleUrl(),this.$parent.goToPage(0)}}},Y=M,A=Object(m["a"])(Y,q,P,!1,null,null,null),z=A.exports,B=s("6c44"),J={beforeMount:function(){this.urls=urls,this.choices=choices},mounted:function(){var e=this;this.$route?this.handleRouteUpdate(this.$route):this.updateSearchFormFields(),w.$on("resetField",(function(t){e.reset_field(t)}))},watch:{$route:function(e,t){this.handleRouteUpdate(e,t)},results:function(){this.results.length&&!this.resultsShown&&(this.resultsShown=!0)},resultsShown:function(){var e="col-md-12";this.display_class=this.results.length?"results-shown":e},endpoint:function(){this.fields=this.endpoints[this.endpoint]}},components:{SearchForm:E,ResultList:z},data:function(){return{title:"Search",hitcount:null,page:0,fields:[],chosen_fields:[],results:[],resultsType:"",resultsShown:!1,first_result_number:null,last_result_number:null,showLoading:!1,cursors:[],endpoint:"cases",page_size:10,choices:{},cursor:null,last_page:!0,first_page:!0,field_errors:{},search_error:null,display_class:"",endpoints:{cases:[{name:"search",value:"",label:"Full-text search",type:"text",placeholder:"Enter keyword or phrase",info:"Terms stemmed and combined using AND. Words in quotes searched as phrases.",default:!0},{name:"decision_date_min",label:"Date from YYYY-MM-DD",placeholder:"YYYY-MM-DD",type:"text",value:""},{name:"decision_date_max",value:"",label:"Date to YYYY-MM-DD",placeholder:"YYYY-MM-DD",type:"text"},{name:"name_abbreviation",label:"Case name abbreviation",value:"",placeholder:"Enter case name abbreviation e.g. Taylor v. Sprinkle"},{name:"docket_number",value:"",label:"Docket number",placeholder:"e.g. Civ. No. 74-289"},{name:"reporter",value:"",label:"Reporter",choices:"reporter"},{name:"jurisdiction",value:"",label:"Jurisdiction",choices:"jurisdiction"},{name:"cite",value:"",label:"Citation e.g. 1 Ill. 17",placeholder:"e.g. 1 Ill. 17"},{name:"court",value:"",label:"Court",placeholder:"e.g. ill-app-ct",hidden:!0}],courts:[{name:"name",value:"",label:"Name e.g. 'Illinois Supreme Court'",placeholder:"e.g. 'Illinois Supreme Court'",default:!0},{name:"jurisdiction",value:"",label:"Jurisdiction",choices:"jurisdiction"},{name:"name_abbreviation",value:"",placeholder:"e.g. 'Ill.'",label:"Name abbreviation e.g. 'Ill.'"},{name:"slug",value:"",label:"Slug e.g. ill-app-ct",placeholder:"e.g. ill-app-ct"}],jurisdictions:[{name:"name_long",value:"",label:"Long Name e.g. 'Illinois'",default:!0},{name:"name",value:"",label:"Name e.g. 'Ill.'"},{name:"whitelisted",value:"",label:"Whitelisted Jurisdiction",choices:"whitelisted",info:"Whitelisted jurisdictions are not subject to the 500 case per day access limitation."}],reporters:[{name:"full_name",value:"",label:"Full Name",default:!0},{name:"jurisdiction",value:"",label:"Jurisdiction",choices:"jurisdiction"},{name:"short_name",value:"",label:"Short Name",placeholder:"e.g. 'Ill. App.'"},{name:"start_year",value:"",type:"number",min:"1640",max:"2018",label:"Start Year",placeholder:"e.g. '1893'",info:"Year in which the reporter began publishing."},{name:"end_year",value:"",type:"number",min:"1640",max:"2018",label:"End Year",placeholder:"e.g. '1894'",info:"Year in which the reporter stopped publishing."}]},sort_field:{name:"ordering",value:"relevance",label:"Result Sorting",choices:"sort"},query_url:""}},methods:{reset_field:function(e){this.fields.map((function(t){t.name===e&&(t.value="")})),this.assembleUrl(),this.newSearch()},create_chosen_fields:function(){this.chosen_fields=JSON.parse(JSON.stringify(this.fields))},routeComparisonString:function(e){if(!e)return"";var t={cursor:!0,page:!0},s=e.query,a=Object.keys(s).filter((function(e){return!t[e]}));return a.sort(),e.params.endpoint+"|"+a.map((function(e){return"".concat(e,":").concat(s[e])})).join("|")},updateSearchFormFields:function(e){var t=this.endpoints[this.endpoint];t.forEach((function(s){s&&e[s.name]&&(s.value=e[s.name],t[s]=s)})),this.fields=t},handleRouteUpdate:function(e,t){var s=this,a=e.query;this.routeComparisonString(e)!==this.routeComparisonString(t)&&(e.name&&(this.endpoint=e.params.endpoint),this.updateSearchFormFields(a),this.resetResults());var r=a.page?parseInt(a.page)-1:void 0;r>=0&&(this.page=r,a.cursor&&(this.cursors[this.page]=a.cursor),(0===this.page||this.results[this.page]||this.cursors[this.page])&&this.getResultsPage().then((function(){s.scrollToResults(),s.last_page=!s.cursors[s.page+1],s.first_page=0===s.page,s.first_result_number=1+s.page_size*s.page,s.last_result_number=s.first_result_number+s.results[s.page].length-1}))),this.create_chosen_fields()},newSearch:function(){this.create_chosen_fields(),this.goToPage(0)},nextPage:function(){this.goToPage(this.page+1)},prevPage:function(){this.goToPage(this.page-1)},goToPage:function(e){this.page=e;var t={page:this.page+1};this.cursors[this.page]&&(t.cursor=this.cursors[this.page]);var s,a=Object(o["a"])(this.fields);try{for(a.s();!(s=a.n()).done;){var r=s.value;r.value&&(t[r.name]=r.value)}}catch(l){a.e(l)}finally{a.f()}this.sort_field["value"]&&(t[this.sort_field["name"]]=this.sort_field["value"]),this.$router.push({name:"endpoint",params:{endpoint:this.endpoint},query:t})},getResultsPage:function(){var e=this;if(this.results[this.page])return Promise.resolve();this.updateQueryURL(),this.search_error="",this.field_errors={};var t=Math.random();return this.currentFetchID=t,fetch(this.query_url).then((function(s){if(t!==e.currentFetchID)throw"canceled";if(!s.ok)throw s;return s.json()})).then((function(t){e.hitcount=t.count;var s=t.next,a=t.previous;e.page>1&&!e.cursors[e.page-1]&&a&&(e.cursors[e.page-1]=e.getCursorFromUrl(a)),!e.cursors[e.page+1]&&s&&(e.cursors[e.page+1]=e.getCursorFromUrl(s)),e.$set(e.results,e.page,t.results),e.resultsType=e.endpoint,e.showLoading=!1})).catch((function(t){if("canceled"!==t){if(e.showLoading=!1,e.scrollToSearchForm(),400===t.status&&e.field_errors)return t.json().then((function(s){throw e.field_errors=s,t}));throw t.status?e.search_error="Search error: API returned "+t.status+" for the query "+e.query_url:e.search_error="Search error: failed to load results from "+e.query_url,console.log("Search error:",t),t}})).catch((function(){}))},resetResults:function(){this.title="Search",this.hitcount=null,this.page=0,this.results=[],this.first_result_number=null,this.last_result_number=null,this.cursors=[],this.last_page=!0,this.first_page=!0},seeCases:function(e,t){var s;this.$router.push({name:"endpoint",params:{endpoint:"cases"},query:(s={},Object(n["a"])(s,e,t),Object(n["a"])(s,"page",1),s)})},getCursorFromUrl:function(e){try{return new URL(e).searchParams.get("cursor")}catch(t){return null}},scrollToResults:function(){this.scrollTo("#results_count_focus")},scrollToSearchForm:function(){this.scrollTo("#form-errors-heading")},scrollTo:function(e){setTimeout((function(){var t=document.querySelector(e);t.focus({preventScroll:!0}),t.scrollIntoView({behavior:"smooth",block:"nearest",inline:"start"})}))},assembleUrl:function(e){var t={};return t.page_size=e||this.page_size,this.cursors[this.page]&&(t.cursor=this.cursors[this.page]),this.fields.forEach((function(e){e["value"]&&(t[e["name"]]=e["value"])})),this.sort_field["value"]&&(t[this.sort_field["name"]]=this.sort_field["value"]),"".concat(this.urls.api_root).concat(this.endpoint,"/?").concat(Object(B["a"])(t))},updateQueryURL:function(){this.query_url=this.assembleUrl()}}},V=J,Q=Object(m["a"])(V,l,i,!1,null,null,null),H=Q.exports;a["default"].config.devtools=!0,a["default"].config.productionTip=!1,a["default"].use(r["a"]);var W=new r["a"]({routes:[{path:"/:endpoint",component:H,name:"endpoint"},{path:"/"},{path:"*",redirect:"/"}]});new a["default"]({el:"#app",components:{Main:H},template:"<Main/>",router:W})},e1b2:function(e,t,s){"use strict";s.d(t,"a",(function(){return a})),s.d(t,"b",(function(){return r}));var a=function(){var e=this,t=e.$createElement,s=e._self._c||t;return s("li",{staticClass:"result"},[s("div",{staticClass:"result-title row"},[s("div",{staticClass:"col-md-9"},[s("a",{staticClass:"simple",attrs:{target:"_blank",href:e.$parent.metadata_view_url("reporter",e.result.id)},domProps:{textContent:e._s(e.result.full_name)}})]),s("div",{staticClass:"col-md-3 decision-date"},[s("a",{staticClass:"see-cases",on:{click:function(t){return e.$parent.$emit("see-cases","reporter",e.result.slug)}}},[e._v(" See cases ")])])])])},r=[]},e5f3:function(e,t){e.exports={props:["result"]}},f519:function(e,t){e.exports={props:["result"]}},f789:function(e,t,s){"use strict";s.d(t,"a",(function(){return a})),s.d(t,"b",(function(){return r}));var a=function(){var e=this,t=e.$createElement,s=e._self._c||t;return s("li",{staticClass:"result"},[s("div",{staticClass:"result-title row"},[s("div",{staticClass:"col-md-9"},[s("a",{staticClass:"simple",attrs:{target:"_blank",href:e.$parent.metadata_view_url("court",e.result.id)},domProps:{textContent:e._s(e.result.name)}})]),s("div",{staticClass:"col-md-3 decision-date"},[s("a",{staticClass:"see-cases",on:{click:function(t){return e.$parent.$emit("see-cases","court",e.result.slug)}}},[e._v(" See cases ")])])])])},r=[]}});
//# sourceMappingURL=search.cbea5e58.js.map