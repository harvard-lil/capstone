(function(r){function e(e){for(var t,u,a=e[0],c=e[1],l=e[2],p=0,s=[];p<a.length;p++)u=a[p],Object.prototype.hasOwnProperty.call(o,u)&&o[u]&&s.push(o[u][0]),o[u]=0;for(t in c)Object.prototype.hasOwnProperty.call(c,t)&&(r[t]=c[t]);f&&f(e);while(s.length)s.shift()();return i.push.apply(i,l||[]),n()}function n(){for(var r,e=0;e<i.length;e++){for(var n=i[e],t=!0,a=1;a<n.length;a++){var c=n[a];0!==o[c]&&(t=!1)}t&&(i.splice(e--,1),r=u(u.s=n[0]))}return r}var t={},o={limericks:0},i=[];function u(e){if(t[e])return t[e].exports;var n=t[e]={i:e,l:!1,exports:{}};return r[e].call(n.exports,n,n.exports,u),n.l=!0,n.exports}u.m=r,u.c=t,u.d=function(r,e,n){u.o(r,e)||Object.defineProperty(r,e,{enumerable:!0,get:n})},u.r=function(r){"undefined"!==typeof Symbol&&Symbol.toStringTag&&Object.defineProperty(r,Symbol.toStringTag,{value:"Module"}),Object.defineProperty(r,"__esModule",{value:!0})},u.t=function(r,e){if(1&e&&(r=u(r)),8&e)return r;if(4&e&&"object"===typeof r&&r&&r.__esModule)return r;var n=Object.create(null);if(u.r(n),Object.defineProperty(n,"default",{enumerable:!0,value:r}),2&e&&"string"!=typeof r)for(var t in r)u.d(n,t,function(e){return r[e]}.bind(null,t));return n},u.n=function(r){var e=r&&r.__esModule?function(){return r["default"]}:function(){return r};return u.d(e,"a",e),e},u.o=function(r,e){return Object.prototype.hasOwnProperty.call(r,e)},u.p="/static/dist/";var a=window["webpackJsonp"]=window["webpackJsonp"]||[],c=a.push.bind(a);a.push=e,a=a.slice();for(var l=0;l<a.length;l++)e(a[l]);var f=c;i.push([2,"chunk-common"]),n()})({2:function(r,e,n){r.exports=n("3be4")},"3be4":function(r,e,n){"use strict";n.r(e);n("581e"),n("494a");var t=n("a881"),o=n.n(t);function i(){var r=limericks,e=u(r["long"],3),n=u(r["short"],2);return[e[0],e[1],n[0],n[1],e[2]]}function u(r,e){var n=c(r),t=c(n),o=l(t,e),i=[];for(var u in o){var f=Math.floor(Math.random()*o[u].length),p=a(o[u][f]);i.push(p)}return i}function a(r){return r}function c(r){var e=Object.keys(r),n=e.length,t=Math.floor(Math.random()*n),o=e[t];return r[o]}function l(r,e){var n,t,o=Object.keys(r),i=o.slice(0),u=o.length;while(u--)t=Math.floor((u+1)*Math.random()),n=i[t],i[t]=i[u],i[u]=n;var a=i.slice(0,e),c=[];for(var l in a){var f=a[l];c.push(r[f])}return c}var f=function(){var r=o()(".limerick-body");r.empty();var e=i();for(var n in e)r.append(e[n]+"<br/>")};o()((function(){f(),o()("#generate-limericks").click((function(){f()}))}))}});
//# sourceMappingURL=limericks.3b2c06ec.js.map