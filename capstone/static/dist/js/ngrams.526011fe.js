(function(e){function t(t){for(var a,i,o=t[0],c=t[1],l=t[2],d=0,f=[];d<o.length;d++)i=o[d],r[i]&&f.push(r[i][0]),r[i]=0;for(a in c)Object.prototype.hasOwnProperty.call(c,a)&&(e[a]=c[a]);u&&u(t);while(f.length)f.shift()();return n.push.apply(n,l||[]),s()}function s(){for(var e,t=0;t<n.length;t++){for(var s=n[t],a=!0,o=1;o<s.length;o++){var c=s[o];0!==r[c]&&(a=!1)}a&&(n.splice(t--,1),e=i(i.s=s[0]))}return e}var a={},r={ngrams:0},n=[];function i(t){if(a[t])return a[t].exports;var s=a[t]={i:t,l:!1,exports:{}};return e[t].call(s.exports,s,s.exports,i),s.l=!0,s.exports}i.m=e,i.c=a,i.d=function(e,t,s){i.o(e,t)||Object.defineProperty(e,t,{enumerable:!0,get:s})},i.r=function(e){"undefined"!==typeof Symbol&&Symbol.toStringTag&&Object.defineProperty(e,Symbol.toStringTag,{value:"Module"}),Object.defineProperty(e,"__esModule",{value:!0})},i.t=function(e,t){if(1&t&&(e=i(e)),8&t)return e;if(4&t&&"object"===typeof e&&e&&e.__esModule)return e;var s=Object.create(null);if(i.r(s),Object.defineProperty(s,"default",{enumerable:!0,value:e}),2&t&&"string"!=typeof e)for(var a in e)i.d(s,a,function(t){return e[t]}.bind(null,a));return s},i.n=function(e){var t=e&&e.__esModule?function(){return e["default"]}:function(){return e};return i.d(t,"a",t),t},i.o=function(e,t){return Object.prototype.hasOwnProperty.call(e,t)},i.p="/static/dist/";var o=window["webpackJsonp"]=window["webpackJsonp"]||[],c=o.push.bind(o);o.push=t,o=o.slice();for(var l=0;l<o.length;l++)t(o[l]);var u=c;n.push([5,"chunk-vendors"]),s()})({"0fd5":function(e,t,s){var a={"./af":"8206","./af.js":"8206","./ar":"cdac","./ar-dz":"7f26","./ar-dz.js":"7f26","./ar-kw":"8e88","./ar-kw.js":"8e88","./ar-ly":"cd65","./ar-ly.js":"cd65","./ar-ma":"e8d6","./ar-ma.js":"e8d6","./ar-sa":"a284","./ar-sa.js":"a284","./ar-tn":"64f7","./ar-tn.js":"64f7","./ar.js":"cdac","./az":"b139","./az.js":"b139","./be":"98e2","./be.js":"98e2","./bg":"a1a5","./bg.js":"a1a5","./bm":"4d0d","./bm.js":"4d0d","./bn":"e8ae","./bn.js":"e8ae","./bo":"bcf2","./bo.js":"bcf2","./br":"69f1","./br.js":"69f1","./bs":"24d1","./bs.js":"24d1","./ca":"3507","./ca.js":"3507","./cs":"d15f","./cs.js":"d15f","./cv":"7bfe","./cv.js":"7bfe","./cy":"1d35","./cy.js":"1d35","./da":"a019","./da.js":"a019","./de":"0cfa","./de-at":"edea","./de-at.js":"edea","./de-ch":"9aae","./de-ch.js":"9aae","./de.js":"0cfa","./dv":"1722","./dv.js":"1722","./el":"5390","./el.js":"5390","./en-SG":"2088","./en-SG.js":"2088","./en-au":"dad9","./en-au.js":"dad9","./en-ca":"6f13","./en-ca.js":"6f13","./en-gb":"6267","./en-gb.js":"6267","./en-ie":"80b1","./en-ie.js":"80b1","./en-il":"ad38","./en-il.js":"ad38","./en-nz":"39db","./en-nz.js":"39db","./eo":"1a30","./eo.js":"1a30","./es":"48a3","./es-do":"f306","./es-do.js":"f306","./es-us":"60bf","./es-us.js":"60bf","./es.js":"48a3","./et":"f891","./et.js":"f891","./eu":"a403","./eu.js":"a403","./fa":"ce14","./fa.js":"ce14","./fi":"fc14","./fi.js":"fc14","./fo":"2bf2","./fo.js":"2bf2","./fr":"c1e8","./fr-ca":"50a2","./fr-ca.js":"50a2","./fr-ch":"b087","./fr-ch.js":"b087","./fr.js":"c1e8","./fy":"4665","./fy.js":"4665","./ga":"b396","./ga.js":"b396","./gd":"056c","./gd.js":"056c","./gl":"efde","./gl.js":"efde","./gom-latn":"8e2c","./gom-latn.js":"8e2c","./gu":"533d","./gu.js":"533d","./he":"7520","./he.js":"7520","./hi":"d2f3","./hi.js":"d2f3","./hr":"7e79","./hr.js":"7e79","./hu":"148f","./hu.js":"148f","./hy-am":"6711","./hy-am.js":"6711","./id":"2b10","./id.js":"2b10","./is":"1feb","./is.js":"1feb","./it":"1b21","./it-ch":"8d2c","./it-ch.js":"8d2c","./it.js":"1b21","./ja":"926e","./ja.js":"926e","./jv":"5a78","./jv.js":"5a78","./ka":"5975","./ka.js":"5975","./kk":"cc93","./kk.js":"cc93","./km":"66e1","./km.js":"66e1","./kn":"5421","./kn.js":"5421","./ko":"1297","./ko.js":"1297","./ku":"16f8","./ku.js":"16f8","./ky":"3df9","./ky.js":"3df9","./lb":"c124","./lb.js":"c124","./lo":"20a5","./lo.js":"20a5","./lt":"c14a","./lt.js":"c14a","./lv":"c553","./lv.js":"c553","./me":"ae25","./me.js":"ae25","./mi":"6f56","./mi.js":"6f56","./mk":"c8fc","./mk.js":"c8fc","./ml":"752d","./ml.js":"752d","./mn":"f09e","./mn.js":"f09e","./mr":"0a56","./mr.js":"0a56","./ms":"55b6","./ms-my":"a9e9","./ms-my.js":"a9e9","./ms.js":"55b6","./mt":"624b","./mt.js":"624b","./my":"e256","./my.js":"e256","./nb":"e1d5","./nb.js":"e1d5","./ne":"761a","./ne.js":"761a","./nl":"a0f2","./nl-be":"5cb2","./nl-be.js":"5cb2","./nl.js":"a0f2","./nn":"4fda","./nn.js":"4fda","./pa-in":"2f2f","./pa-in.js":"2f2f","./pl":"317f","./pl.js":"317f","./pt":"5553","./pt-br":"a9ab","./pt-br.js":"a9ab","./pt.js":"5553","./ro":"db12","./ro.js":"db12","./ru":"7aa4","./ru.js":"7aa4","./sd":"e87b","./sd.js":"e87b","./se":"a296","./se.js":"a296","./si":"51ec","./si.js":"51ec","./sk":"608b","./sk.js":"608b","./sl":"b367","./sl.js":"b367","./sq":"f68f","./sq.js":"f68f","./sr":"0991","./sr-cyrl":"c577","./sr-cyrl.js":"c577","./sr.js":"0991","./ss":"cf76","./ss.js":"cf76","./sv":"0153","./sv.js":"0153","./sw":"cb6f","./sw.js":"cb6f","./ta":"8bfa","./ta.js":"8bfa","./te":"668b","./te.js":"668b","./tet":"eae7","./tet.js":"eae7","./tg":"70b1","./tg.js":"70b1","./th":"7180","./th.js":"7180","./tl-ph":"f8bb","./tl-ph.js":"f8bb","./tlh":"b026","./tlh.js":"b026","./tr":"371d","./tr.js":"371d","./tzl":"c744","./tzl.js":"c744","./tzm":"787a","./tzm-latn":"71e0","./tzm-latn.js":"71e0","./tzm.js":"787a","./ug-cn":"6b5c","./ug-cn.js":"6b5c","./uk":"8c0c","./uk.js":"8c0c","./ur":"519e","./ur.js":"519e","./uz":"7982","./uz-latn":"3137","./uz-latn.js":"3137","./uz.js":"7982","./vi":"ae22","./vi.js":"ae22","./x-pseudo":"1129","./x-pseudo.js":"1129","./yo":"b4bf","./yo.js":"b4bf","./zh-cn":"fdc4","./zh-cn.js":"fdc4","./zh-hk":"747d","./zh-hk.js":"747d","./zh-tw":"d3e0","./zh-tw.js":"d3e0"};function r(e){var t=n(e);return s(t)}function n(e){var t=a[e];if(!(t+1)){var s=new Error("Cannot find module '"+e+"'");throw s.code="MODULE_NOT_FOUND",s}return t}r.keys=function(){return Object.keys(a)},r.resolve=n,e.exports=r,r.id="0fd5"},5:function(e,t,s){e.exports=s("b9d6")},b9d6:function(e,t,s){"use strict";s.r(t);var a,r,n=s("a4b5"),i=s("4af9"),o=function(){var e=this,t=e.$createElement,s=e._self._c||t;return s("div",[e._m(0),s("div",{staticClass:"form-group"},[s("div",{staticClass:"row"},[s("input",{directives:[{name:"model",rawName:"v-model.trim",value:e.textToGraph,expression:"textToGraph",modifiers:{trim:!0}}],staticClass:"col-lg-12 text-to-graph",attrs:{placeholder:"Your text here"},domProps:{value:e.textToGraph},on:{keyup:function(t){return!t.type.indexOf("key")&&e._k(t.keyCode,"enter",13,t.key,"Enter")?null:e.createGraph()},input:function(t){t.target.composing||(e.textToGraph=t.target.value.trim())},blur:function(t){return e.$forceUpdate()}}}),s("div",{staticClass:"col-lg-12 description small"},[e._v("Separate entries using commas")])]),s("div",{staticClass:"row"},[s("div",{staticClass:"col-lg-6 form-group-elements"},[s("label",{attrs:{for:"min-year"}},[e._v("From")]),s("input",{directives:[{name:"model",rawName:"v-model.number",value:e.minYear,expression:"minYear",modifiers:{number:!0}}],attrs:{id:"min-year",type:"number",min:"1640",max:"2018"},domProps:{value:e.minYear},on:{keyup:function(t){return!t.type.indexOf("key")&&e._k(t.keyCode,"enter",13,t.key,"Enter")?null:e.createGraph()},input:function(t){t.target.composing||(e.minYear=e._n(t.target.value))},blur:function(t){return e.$forceUpdate()}}}),e._v("\n         \n        "),s("label",{attrs:{for:"max-year"}},[e._v("To")]),s("input",{directives:[{name:"model",rawName:"v-model.number",value:e.maxYear,expression:"maxYear",modifiers:{number:!0}}],attrs:{id:"max-year",type:"number",min:"1640",max:"2018"},domProps:{value:e.maxYear},on:{keyup:function(t){return!t.type.indexOf("key")&&e._k(t.keyCode,"enter",13,t.key,"Enter")?null:e.createGraph()},input:function(t){t.target.composing||(e.maxYear=e._n(t.target.value))},blur:function(t){return e.$forceUpdate()}}})]),s("div",{staticClass:"col-lg-4 text-right"},[s("input",{staticClass:"dropdown-toggle btn-secondary",attrs:{type:"button",id:"jurisdictions",value:"Jurisdictions","data-toggle":"dropdown","aria-haspopup":"true","aria-expanded":"false"}}),s("div",{staticClass:"dropdown dropdown-menu",attrs:{"aria-labelledby":"jurisdictions"}},e._l(e.jurisdictions,function(t){return s("button",{key:t[0],staticClass:"dropdown-item",class:{active:e.selectedJurs.indexOf(t)>-1},attrs:{type:"button"},on:{click:function(s){return e.toggleJur(t)}}},[e._v("\n            "+e._s(t[1])+"\n          ")])}),0)]),s("div",{staticClass:"col-lg-2 text-right"},[s("button",{staticClass:"btn-create btn-primary",on:{click:e.createGraph}},[e._v("\n          Graph\n        ")])])]),e.errors.length?s("div",{staticClass:"row"},[s("div",{staticClass:"small alert-danger"},[s("span",[e._v(e._s(e.errors))])])]):e._e(),s("div",{staticClass:"row"},[s("div",{staticClass:"selected-jurs"},[e.selectedJurs.length?s("span",{staticClass:"small"},[e._v("Searching selected:")]):s("span",{staticClass:"small"},[e._v("Searching all jurisdictions")]),e._l(e.selectedJurs,function(t){return s("span",{key:t[0],staticClass:"small selected-jur",on:{click:function(s){return e.toggleJur(t)}}},[e._v("\n          "+e._s(t[1])+"\n        ")])})],2)]),s("br")]),s("div",{staticClass:"graph"},[s("div",{staticClass:"container graph-container"},[s("line-example",{attrs:{chartData:e.chartData}})],1)])])},c=[function(){var e=this,t=e.$createElement,s=e._self._c||t;return s("div",{staticClass:"page-title"},[s("h1",[e._v("Ngrams")]),s("p",[e._v("Navigate the distribution of words and phrases across U.S. case law with keywords, date ranges, and\n      jurisdictions.")])])}],l=(s("e1a2"),s("8430")),u=(s("2bf3"),s("baa4"),s("fa38"),s("0012"),s("5b54"),s("6ac6"),s("20a4"),s("7b62"),s("92ea")),d=u["b"].reactiveProp,f={extends:u["a"],props:["chartData"],mixins:[d],data:function(){return{options:{responsive:!0,maintainAspectRatio:!1,legend:{labels:{boxWidth:20}},scales:{yAxes:[{gridLines:{color:"rgba(0, 0, 0, 0)"},ticks:{beginAtZero:!0,callback:function(e){if(e%1===0)return e}}}],xAxes:[{gridLines:{color:"rgba(0, 0, 0, 0)"},ticks:{beginAtZero:!0}}]}}}},mounted:function(){this.renderChart(this.chartData,this.options)}},b=f,h=s("a6c2"),p=Object(h["a"])(b,a,r,!1,null,null,null),j=p.exports,m={name:"Main",components:{"line-example":j},beforeMount:function(){this.jurisdictions=snippets.jurisdictions,this.urls=urls,this.$route.query.q&&(this.textToGraph=this.$route.query.q)},mounted:function(){this.createGraph()},data:function(){return{chartData:null,textToGraph:"apple pie, blueberry pie",minYear:1800,maxYear:2e3,minPossible:1640,maxPossible:2018,jurisdictions:{},urls:{},selectedJurs:[],colors:["#0276FF","#E878FF","#EDA633","#FF654D","#6350FD"],errors:""}},methods:{isValidYear:function(e){return e>=this.minPossible&&e<=this.maxPossible},isValidText:function(){return this.textToGraph.length>0},range:function(e,t){var s=arguments.length>2&&void 0!==arguments[2]?arguments[2]:1;return e=Number(e),t=Number(t),Array(Math.ceil((t-e)/s)).fill(e).map(function(e,t){return e+t*s})},getSelectedJurs:function(){return this.selectedJurs.map(function(e){return e[0]})},getTerms:function(e){var t=e.split(",");return t.map(function(e){return e.trim()})},inputsAreValid:function(){return this.minYear>this.maxYear||!this.isValidYear(this.minYear)||!this.isValidYear(this.maxYear)?(this.errors="Please choose valid years. Years must be between "+this.minPossible+" and "+this.maxPossible+".",!1):!!this.isValidText()||(this.errors="Please enter text",!1)},createGraph:function(){var e=this;if(this.inputsAreValid()){this.errors="";var t=this.getTerms(this.textToGraph),s=this.range(this.minYear,this.maxYear);this.chartData={labels:s,datasets:[]};var a=this.getSelectedJurs();a.splice(0,0,"");var r=a.join("&jurisdiction=");this.$router.push({path:"/",query:{q:this.textToGraph}});var n=!0,i=!1,o=void 0;try{for(var c,l=t[Symbol.iterator]();!(n=(c=l.next()).done);n=!0){var u=c.value,d=encodeURI(this.urls.api_root+"ngrams/?q="+u+r);fetch(d).then(function(e){if(!e.ok)throw e;return e.json()}).then(function(t){var a=e.parseResponse(t.results);e.graphResults(a,s)}).catch(function(t){"canceled"===t&&(e.errors="Something went wrong. Please try again.")})}}catch(f){i=!0,o=f}finally{try{n||null==l.return||l.return()}finally{if(i)throw o}}}},graphResults:function(e,t){for(var s=this.chartData.datasets,a=0,r=Object.entries(e);a<r.length;a++){var n=Object(l["a"])(r[a],2),i=n[0],o=n[1],c=this.colors.length>=1?this.colors.pop():"#"+(16777215*Math.random()<<0).toString(16);s.push({label:i,backgroundColor:c,borderWidth:0,borderRadius:100,data:o})}this.chartData={labels:t,datasets:s}},parseResponse:function(e){for(var t={},s=0,a=Object.entries(e);s<a.length;s++)for(var r=Object(l["a"])(a[s],2),n=r[0],i=r[1],o=0,c=Object.entries(i);o<c.length;o++){var u=Object(l["a"])(c[o],2),d=u[0],f=u[1],b=[],h=!0,p=!1,j=void 0;try{for(var m,v=f[Symbol.iterator]();!(h=(m=v.next()).done);h=!0){var g=m.value,y=g["year"];"total"!==y&&(y>=this.minYear&&y<=this.maxYear&&(b[y-this.minYear]=g["count"][0]))}}catch(x){p=!0,j=x}finally{try{h||null==v.return||v.return()}finally{if(p)throw j}}t[("total"===d?"":d+": ")+n]=b}return t},toggleJur:function(e){this.selectedJurs.indexOf(e)>-1?this.selectedJurs.splice(this.selectedJurs.indexOf(e),1):this.selectedJurs.push(e)}}},v=m,g=Object(h["a"])(v,o,c,!1,null,null,null),y=g.exports;n["a"].config.devtools=!0,n["a"].config.productionTip=!1,n["a"].use(i["a"]);var x=new i["a"]({routes:[{path:"/",component:y,name:"main"},{path:"*",redirect:"/"}]});new n["a"]({el:"#app",components:{Main:y},template:"<Main/>",router:x})}});
//# sourceMappingURL=ngrams.526011fe.js.map