/**!
 * @fileOverview Kickass library to create and place poppers near their reference elements.
 * @version 1.16.1
 * @license
 * Copyright (c) 2016 Federico Zivolo and contributors
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 */var T=typeof window!="undefined"&&typeof document!="undefined"&&typeof navigator!="undefined",pe=function(){for(var e=["Edge","Trident","Firefox"],t=0;t<e.length;t+=1)if(T&&navigator.userAgent.indexOf(e[t])>=0)return 1;return 0}();function ce(e){var t=!1;return function(){t||(t=!0,window.Promise.resolve().then(function(){t=!1,e()}))}}function de(e){var t=!1;return function(){t||(t=!0,setTimeout(function(){t=!1,e()},pe))}}var he=T&&window.Promise,ve=he?ce:de;function K(e){var t={};return e&&t.toString.call(e)==="[object Function]"}function O(e,t){if(e.nodeType!==1)return[];var r=e.ownerDocument.defaultView,n=r.getComputedStyle(e,null);return t?n[t]:n}function I(e){return e.nodeName==="HTML"?e:e.parentNode||e.host}function C(e){if(!e)return document.body;switch(e.nodeName){case"HTML":case"BODY":return e.ownerDocument.body;case"#document":return e.body}var t=O(e),r=t.overflow,n=t.overflowX,o=t.overflowY;return/(auto|scroll|overlay)/.test(r+o+n)?e:C(I(e))}function X(e){return e&&e.referenceNode?e.referenceNode:e}var U=T&&!!(window.MSInputMethodContext&&document.documentMode),Y=T&&/MSIE 10/.test(navigator.userAgent);function L(e){return e===11?U:e===10?Y:U||Y}function x(e){if(!e)return document.documentElement;for(var t=L(10)?document.body:null,r=e.offsetParent||null;r===t&&e.nextElementSibling;)r=(e=e.nextElementSibling).offsetParent;var n=r&&r.nodeName;return!n||n==="BODY"||n==="HTML"?e?e.ownerDocument.documentElement:document.documentElement:["TH","TD","TABLE"].indexOf(r.nodeName)!==-1&&O(r,"position")==="static"?x(r):r}function me(e){var t=e.nodeName;return t==="BODY"?!1:t==="HTML"||x(e.firstElementChild)===e}function R(e){return e.parentNode!==null?R(e.parentNode):e}function D(e,t){if(!e||!e.nodeType||!t||!t.nodeType)return document.documentElement;var r=e.compareDocumentPosition(t)&Node.DOCUMENT_POSITION_FOLLOWING,n=r?e:t,o=r?t:e,i=document.createRange();i.setStart(n,0),i.setEnd(o,0);var f=i.commonAncestorContainer;if(e!==f&&t!==f||n.contains(o))return me(f)?f:x(f);var s=R(e);return s.host?D(s.host,t):D(e,R(t).host)}function P(e){var t=arguments.length>1&&arguments[1]!==void 0?arguments[1]:"top",r=t==="top"?"scrollTop":"scrollLeft",n=e.nodeName;if(n==="BODY"||n==="HTML"){var o=e.ownerDocument.documentElement,i=e.ownerDocument.scrollingElement||o;return i[r]}return e[r]}function ge(e,t){var r=arguments.length>2&&arguments[2]!==void 0?arguments[2]:!1,n=P(t,"top"),o=P(t,"left"),i=r?-1:1;return e.top+=n*i,e.bottom+=n*i,e.left+=o*i,e.right+=o*i,e}function _(e,t){var r=t==="x"?"Left":"Top",n=r==="Left"?"Right":"Bottom";return parseFloat(e["border"+r+"Width"])+parseFloat(e["border"+n+"Width"])}function q(e,t,r,n){return Math.max(t["offset"+e],t["scroll"+e],r["client"+e],r["offset"+e],r["scroll"+e],L(10)?parseInt(r["offset"+e])+parseInt(n["margin"+(e==="Height"?"Top":"Left")])+parseInt(n["margin"+(e==="Height"?"Bottom":"Right")]):0)}function J(e){var t=e.body,r=e.documentElement,n=L(10)&&getComputedStyle(r);return{height:q("Height",t,r,n),width:q("Width",t,r,n)}}var be=function(e,t){if(!(e instanceof t))throw new TypeError("Cannot call a class as a function")},we=function(){function e(t,r){for(var n=0;n<r.length;n++){var o=r[n];o.enumerable=o.enumerable||!1,o.configurable=!0,"value"in o&&(o.writable=!0),Object.defineProperty(t,o.key,o)}}return function(t,r,n){return r&&e(t.prototype,r),n&&e(t,n),t}}(),S=function(e,t,r){return t in e?Object.defineProperty(e,t,{value:r,enumerable:!0,configurable:!0,writable:!0}):e[t]=r,e},g=Object.assign||function(e){for(var t=1;t<arguments.length;t++){var r=arguments[t];for(var n in r)Object.prototype.hasOwnProperty.call(r,n)&&(e[n]=r[n])}return e};function y(e){return g({},e,{right:e.left+e.width,bottom:e.top+e.height})}function W(e){var t={};try{if(L(10)){t=e.getBoundingClientRect();var r=P(e,"top"),n=P(e,"left");t.top+=r,t.left+=n,t.bottom+=r,t.right+=n}else t=e.getBoundingClientRect()}catch{}var o={left:t.left,top:t.top,width:t.right-t.left,height:t.bottom-t.top},i=e.nodeName==="HTML"?J(e.ownerDocument):{},f=i.width||e.clientWidth||o.width,s=i.height||e.clientHeight||o.height,a=e.offsetWidth-f,l=e.offsetHeight-s;if(a||l){var p=O(e);a-=_(p,"x"),l-=_(p,"y"),o.width-=a,o.height-=l}return y(o)}function k(e,t){var r=arguments.length>2&&arguments[2]!==void 0?arguments[2]:!1,n=L(10),o=t.nodeName==="HTML",i=W(e),f=W(t),s=C(e),a=O(t),l=parseFloat(a.borderTopWidth),p=parseFloat(a.borderLeftWidth);r&&o&&(f.top=Math.max(f.top,0),f.left=Math.max(f.left,0));var u=y({top:i.top-f.top-l,left:i.left-f.left-p,width:i.width,height:i.height});if(u.marginTop=0,u.marginLeft=0,!n&&o){var d=parseFloat(a.marginTop),c=parseFloat(a.marginLeft);u.top-=l-d,u.bottom-=l-d,u.left-=p-c,u.right-=p-c,u.marginTop=d,u.marginLeft=c}return(n&&!r?t.contains(s):t===s&&s.nodeName!=="BODY")&&(u=ge(u,t)),u}function ye(e){var t=arguments.length>1&&arguments[1]!==void 0?arguments[1]:!1,r=e.ownerDocument.documentElement,n=k(e,r),o=Math.max(r.clientWidth,window.innerWidth||0),i=Math.max(r.clientHeight,window.innerHeight||0),f=t?0:P(r),s=t?0:P(r,"left"),a={top:f-n.top+n.marginTop,left:s-n.left+n.marginLeft,width:o,height:i};return y(a)}function Q(e){var t=e.nodeName;if(t==="BODY"||t==="HTML")return!1;if(O(e,"position")==="fixed")return!0;var r=I(e);return r?Q(r):!1}function Z(e){if(!e||!e.parentElement||L())return document.documentElement;for(var t=e.parentElement;t&&O(t,"transform")==="none";)t=t.parentElement;return t||document.documentElement}function V(e,t,r,n){var o=arguments.length>4&&arguments[4]!==void 0?arguments[4]:!1,i={top:0,left:0},f=o?Z(e):D(e,X(t));if(n==="viewport")i=ye(f,o);else{var s=void 0;n==="scrollParent"?(s=C(I(t)),s.nodeName==="BODY"&&(s=e.ownerDocument.documentElement)):n==="window"?s=e.ownerDocument.documentElement:s=n;var a=k(s,f,o);if(s.nodeName==="HTML"&&!Q(f)){var l=J(e.ownerDocument),p=l.height,u=l.width;i.top+=a.top-a.marginTop,i.bottom=p+a.top,i.left+=a.left-a.marginLeft,i.right=u+a.left}else i=a}r=r||0;var d=typeof r=="number";return i.left+=d?r:r.left||0,i.top+=d?r:r.top||0,i.right-=d?r:r.right||0,i.bottom-=d?r:r.bottom||0,i}function Ee(e){var t=e.width,r=e.height;return t*r}function ee(e,t,r,n,o){var i=arguments.length>5&&arguments[5]!==void 0?arguments[5]:0;if(e.indexOf("auto")===-1)return e;var f=V(r,n,i,o),s={top:{width:f.width,height:t.top-f.top},right:{width:f.right-t.right,height:f.height},bottom:{width:f.width,height:f.bottom-t.bottom},left:{width:t.left-f.left,height:f.height}},a=Object.keys(s).map(function(d){return g({key:d},s[d],{area:Ee(s[d])})}).sort(function(d,c){return c.area-d.area}),l=a.filter(function(d){var c=d.width,h=d.height;return c>=r.clientWidth&&h>=r.clientHeight}),p=l.length>0?l[0].key:a[0].key,u=e.split("-")[1];return p+(u?"-"+u:"")}function te(e,t,r){var n=arguments.length>3&&arguments[3]!==void 0?arguments[3]:null,o=n?Z(t):D(t,X(r));return k(r,o,n)}function re(e){var t=e.ownerDocument.defaultView,r=t.getComputedStyle(e),n=parseFloat(r.marginTop||0)+parseFloat(r.marginBottom||0),o=parseFloat(r.marginLeft||0)+parseFloat(r.marginRight||0),i={width:e.offsetWidth+o,height:e.offsetHeight+n};return i}function N(e){var t={left:"right",right:"left",bottom:"top",top:"bottom"};return e.replace(/left|right|bottom|top/g,function(r){return t[r]})}function ne(e,t,r){r=r.split("-")[0];var n=re(e),o={width:n.width,height:n.height},i=["right","left"].indexOf(r)!==-1,f=i?"top":"left",s=i?"left":"top",a=i?"height":"width",l=i?"width":"height";return o[f]=t[f]+t[a]/2-n[a]/2,r===s?o[s]=t[s]-n[l]:o[s]=t[N(s)],o}function M(e,t){return Array.prototype.find?e.find(t):e.filter(t)[0]}function Oe(e,t,r){if(Array.prototype.findIndex)return e.findIndex(function(o){return o[t]===r});var n=M(e,function(o){return o[t]===r});return e.indexOf(n)}function ie(e,t,r){var n=r===void 0?e:e.slice(0,Oe(e,"name",r));return n.forEach(function(o){o.function&&console.warn("`modifier.function` is deprecated, use `modifier.fn`!");var i=o.function||o.fn;o.enabled&&K(i)&&(t.offsets.popper=y(t.offsets.popper),t.offsets.reference=y(t.offsets.reference),t=i(t,o))}),t}function xe(){if(!this.state.isDestroyed){var e={instance:this,styles:{},arrowStyles:{},attributes:{},flipped:!1,offsets:{}};e.offsets.reference=te(this.state,this.popper,this.reference,this.options.positionFixed),e.placement=ee(this.options.placement,e.offsets.reference,this.popper,this.reference,this.options.modifiers.flip.boundariesElement,this.options.modifiers.flip.padding),e.originalPlacement=e.placement,e.positionFixed=this.options.positionFixed,e.offsets.popper=ne(this.popper,e.offsets.reference,e.placement),e.offsets.popper.position=this.options.positionFixed?"fixed":"absolute",e=ie(this.modifiers,e),this.state.isCreated?this.options.onUpdate(e):(this.state.isCreated=!0,this.options.onCreate(e))}}function oe(e,t){return e.some(function(r){var n=r.name,o=r.enabled;return o&&n===t})}function $(e){for(var t=[!1,"ms","Webkit","Moz","O"],r=e.charAt(0).toUpperCase()+e.slice(1),n=0;n<t.length;n++){var o=t[n],i=o?""+o+r:e;if(typeof document.body.style[i]!="undefined")return i}return null}function Pe(){return this.state.isDestroyed=!0,oe(this.modifiers,"applyStyle")&&(this.popper.removeAttribute("x-placement"),this.popper.style.position="",this.popper.style.top="",this.popper.style.left="",this.popper.style.right="",this.popper.style.bottom="",this.popper.style.willChange="",this.popper.style[$("transform")]=""),this.disableEventListeners(),this.options.removeOnDestroy&&this.popper.parentNode.removeChild(this.popper),this}function fe(e){var t=e.ownerDocument;return t?t.defaultView:window}function se(e,t,r,n){var o=e.nodeName==="BODY",i=o?e.ownerDocument.defaultView:e;i.addEventListener(t,r,{passive:!0}),o||se(C(i.parentNode),t,r,n),n.push(i)}function Se(e,t,r,n){r.updateBound=n,fe(e).addEventListener("resize",r.updateBound,{passive:!0});var o=C(e);return se(o,"scroll",r.updateBound,r.scrollParents),r.scrollElement=o,r.eventsEnabled=!0,r}function Le(){this.state.eventsEnabled||(this.state=Se(this.reference,this.options,this.state,this.scheduleUpdate))}function Te(e,t){return fe(e).removeEventListener("resize",t.updateBound),t.scrollParents.forEach(function(r){r.removeEventListener("scroll",t.updateBound)}),t.updateBound=null,t.scrollParents=[],t.scrollElement=null,t.eventsEnabled=!1,t}function Ce(){this.state.eventsEnabled&&(cancelAnimationFrame(this.scheduleUpdate),this.state=Te(this.reference,this.state))}function j(e){return e!==""&&!isNaN(parseFloat(e))&&isFinite(e)}function H(e,t){Object.keys(t).forEach(function(r){var n="";["width","height","top","right","bottom","left"].indexOf(r)!==-1&&j(t[r])&&(n="px"),e.style[r]=t[r]+n})}function Me(e,t){Object.keys(t).forEach(function(r){var n=t[r];n!==!1?e.setAttribute(r,t[r]):e.removeAttribute(r)})}function De(e){return H(e.instance.popper,e.styles),Me(e.instance.popper,e.attributes),e.arrowElement&&Object.keys(e.arrowStyles).length&&H(e.arrowElement,e.arrowStyles),e}function Ne(e,t,r,n,o){var i=te(o,t,e,r.positionFixed),f=ee(r.placement,i,t,e,r.modifiers.flip.boundariesElement,r.modifiers.flip.padding);return t.setAttribute("x-placement",f),H(t,{position:r.positionFixed?"fixed":"absolute"}),r}function Be(e,t){var r=e.offsets,n=r.popper,o=r.reference,i=Math.round,f=Math.floor,s=function(w){return w},a=i(o.width),l=i(n.width),p=["left","right"].indexOf(e.placement)!==-1,u=e.placement.indexOf("-")!==-1,d=a%2===l%2,c=a%2===1&&l%2===1,h=t?p||u||d?i:f:s,v=t?i:s;return{left:h(c&&!u&&t?n.left-1:n.left),top:v(n.top),bottom:v(n.bottom),right:h(n.right)}}var Fe=T&&/Firefox/i.test(navigator.userAgent);function Ae(e,t){var r=t.x,n=t.y,o=e.offsets.popper,i=M(e.instance.modifiers,function(E){return E.name==="applyStyle"}).gpuAcceleration;i!==void 0&&console.warn("WARNING: `gpuAcceleration` option moved to `computeStyle` modifier and will not be supported in future versions of Popper.js!");var f=i!==void 0?i:t.gpuAcceleration,s=x(e.instance.popper),a=W(s),l={position:o.position},p=Be(e,window.devicePixelRatio<2||!Fe),u=r==="bottom"?"top":"bottom",d=n==="right"?"left":"right",c=$("transform"),h=void 0,v=void 0;if(u==="bottom"?s.nodeName==="HTML"?v=-s.clientHeight+p.bottom:v=-a.height+p.bottom:v=p.top,d==="right"?s.nodeName==="HTML"?h=-s.clientWidth+p.right:h=-a.width+p.right:h=p.left,f&&c)l[c]="translate3d("+h+"px, "+v+"px, 0)",l[u]=0,l[d]=0,l.willChange="transform";else{var b=u==="bottom"?-1:1,w=d==="right"?-1:1;l[u]=v*b,l[d]=h*w,l.willChange=u+", "+d}var m={"x-placement":e.placement};return e.attributes=g({},m,e.attributes),e.styles=g({},l,e.styles),e.arrowStyles=g({},e.offsets.arrow,e.arrowStyles),e}function ae(e,t,r){var n=M(e,function(s){var a=s.name;return a===t}),o=!!n&&e.some(function(s){return s.name===r&&s.enabled&&s.order<n.order});if(!o){var i="`"+t+"`",f="`"+r+"`";console.warn(f+" modifier is required by "+i+" modifier in order to work, be sure to include it before "+i+"!")}return o}function Re(e,t){var r;if(!ae(e.instance.modifiers,"arrow","keepTogether"))return e;var n=t.element;if(typeof n=="string"){if(n=e.instance.popper.querySelector(n),!n)return e}else if(!e.instance.popper.contains(n))return console.warn("WARNING: `arrow.element` must be child of its popper element!"),e;var o=e.placement.split("-")[0],i=e.offsets,f=i.popper,s=i.reference,a=["left","right"].indexOf(o)!==-1,l=a?"height":"width",p=a?"Top":"Left",u=p.toLowerCase(),d=a?"left":"top",c=a?"bottom":"right",h=re(n)[l];s[c]-h<f[u]&&(e.offsets.popper[u]-=f[u]-(s[c]-h)),s[u]+h>f[c]&&(e.offsets.popper[u]+=s[u]+h-f[c]),e.offsets.popper=y(e.offsets.popper);var v=s[u]+s[l]/2-h/2,b=O(e.instance.popper),w=parseFloat(b["margin"+p]),m=parseFloat(b["border"+p+"Width"]),E=v-e.offsets.popper[u]-w-m;return E=Math.max(Math.min(f[l]-h,E),0),e.arrowElement=n,e.offsets.arrow=(r={},S(r,u,Math.round(E)),S(r,d,""),r),e}function We(e){return e==="end"?"start":e==="start"?"end":e}var ue=["auto-start","auto","auto-end","top-start","top","top-end","right-start","right","right-end","bottom-end","bottom","bottom-start","left-end","left","left-start"],F=ue.slice(3);function G(e){var t=arguments.length>1&&arguments[1]!==void 0?arguments[1]:!1,r=F.indexOf(e),n=F.slice(r+1).concat(F.slice(0,r));return t?n.reverse():n}var A={FLIP:"flip",CLOCKWISE:"clockwise",COUNTERCLOCKWISE:"counterclockwise"};function He(e,t){if(oe(e.instance.modifiers,"inner")||e.flipped&&e.placement===e.originalPlacement)return e;var r=V(e.instance.popper,e.instance.reference,t.padding,t.boundariesElement,e.positionFixed),n=e.placement.split("-")[0],o=N(n),i=e.placement.split("-")[1]||"",f=[];switch(t.behavior){case A.FLIP:f=[n,o];break;case A.CLOCKWISE:f=G(n);break;case A.COUNTERCLOCKWISE:f=G(n,!0);break;default:f=t.behavior}return f.forEach(function(s,a){if(n!==s||f.length===a+1)return e;n=e.placement.split("-")[0],o=N(n);var l=e.offsets.popper,p=e.offsets.reference,u=Math.floor,d=n==="left"&&u(l.right)>u(p.left)||n==="right"&&u(l.left)<u(p.right)||n==="top"&&u(l.bottom)>u(p.top)||n==="bottom"&&u(l.top)<u(p.bottom),c=u(l.left)<u(r.left),h=u(l.right)>u(r.right),v=u(l.top)<u(r.top),b=u(l.bottom)>u(r.bottom),w=n==="left"&&c||n==="right"&&h||n==="top"&&v||n==="bottom"&&b,m=["top","bottom"].indexOf(n)!==-1,E=!!t.flipVariations&&(m&&i==="start"&&c||m&&i==="end"&&h||!m&&i==="start"&&v||!m&&i==="end"&&b),le=!!t.flipVariationsByContent&&(m&&i==="start"&&h||m&&i==="end"&&c||!m&&i==="start"&&b||!m&&i==="end"&&v),z=E||le;(d||w||z)&&(e.flipped=!0,(d||w)&&(n=f[a+1]),z&&(i=We(i)),e.placement=n+(i?"-"+i:""),e.offsets.popper=g({},e.offsets.popper,ne(e.instance.popper,e.offsets.reference,e.placement)),e=ie(e.instance.modifiers,e,"flip"))}),e}function Ie(e){var t=e.offsets,r=t.popper,n=t.reference,o=e.placement.split("-")[0],i=Math.floor,f=["top","bottom"].indexOf(o)!==-1,s=f?"right":"bottom",a=f?"left":"top",l=f?"width":"height";return r[s]<i(n[a])&&(e.offsets.popper[a]=i(n[a])-r[l]),r[a]>i(n[s])&&(e.offsets.popper[a]=i(n[s])),e}function ke(e,t,r,n){var o=e.match(/((?:\-|\+)?\d*\.?\d*)(.*)/),i=+o[1],f=o[2];if(!i)return e;if(f.indexOf("%")===0){var s=void 0;switch(f){case"%p":s=r;break;case"%":case"%r":default:s=n}var a=y(s);return a[t]/100*i}else if(f==="vh"||f==="vw"){var l=void 0;return f==="vh"?l=Math.max(document.documentElement.clientHeight,window.innerHeight||0):l=Math.max(document.documentElement.clientWidth,window.innerWidth||0),l/100*i}else return i}function Ve(e,t,r,n){var o=[0,0],i=["right","left"].indexOf(n)!==-1,f=e.split(/(\+|\-)/).map(function(p){return p.trim()}),s=f.indexOf(M(f,function(p){return p.search(/,|\s/)!==-1}));f[s]&&f[s].indexOf(",")===-1&&console.warn("Offsets separated by white space(s) are deprecated, use a comma (,) instead.");var a=/\s*,\s*|\s+/,l=s!==-1?[f.slice(0,s).concat([f[s].split(a)[0]]),[f[s].split(a)[1]].concat(f.slice(s+1))]:[f];return l=l.map(function(p,u){var d=(u===1?!i:i)?"height":"width",c=!1;return p.reduce(function(h,v){return h[h.length-1]===""&&["+","-"].indexOf(v)!==-1?(h[h.length-1]=v,c=!0,h):c?(h[h.length-1]+=v,c=!1,h):h.concat(v)},[]).map(function(h){return ke(h,d,t,r)})}),l.forEach(function(p,u){p.forEach(function(d,c){j(d)&&(o[u]+=d*(p[c-1]==="-"?-1:1))})}),o}function $e(e,t){var r=t.offset,n=e.placement,o=e.offsets,i=o.popper,f=o.reference,s=n.split("-")[0],a=void 0;return j(+r)?a=[+r,0]:a=Ve(r,i,f,s),s==="left"?(i.top+=a[0],i.left-=a[1]):s==="right"?(i.top+=a[0],i.left+=a[1]):s==="top"?(i.left+=a[0],i.top-=a[1]):s==="bottom"&&(i.left+=a[0],i.top+=a[1]),e.popper=i,e}function je(e,t){var r=t.boundariesElement||x(e.instance.popper);e.instance.reference===r&&(r=x(r));var n=$("transform"),o=e.instance.popper.style,i=o.top,f=o.left,s=o[n];o.top="",o.left="",o[n]="";var a=V(e.instance.popper,e.instance.reference,t.padding,r,e.positionFixed);o.top=i,o.left=f,o[n]=s,t.boundaries=a;var l=t.priority,p=e.offsets.popper,u={primary:function(c){var h=p[c];return p[c]<a[c]&&!t.escapeWithReference&&(h=Math.max(p[c],a[c])),S({},c,h)},secondary:function(c){var h=c==="right"?"left":"top",v=p[h];return p[c]>a[c]&&!t.escapeWithReference&&(v=Math.min(p[h],a[c]-(c==="right"?p.width:p.height))),S({},h,v)}};return l.forEach(function(d){var c=["left","top"].indexOf(d)!==-1?"primary":"secondary";p=g({},p,u[c](d))}),e.offsets.popper=p,e}function ze(e){var t=e.placement,r=t.split("-")[0],n=t.split("-")[1];if(n){var o=e.offsets,i=o.reference,f=o.popper,s=["bottom","top"].indexOf(r)!==-1,a=s?"left":"top",l=s?"width":"height",p={start:S({},a,i[a]),end:S({},a,i[a]+i[l]-f[l])};e.offsets.popper=g({},f,p[n])}return e}function Ue(e){if(!ae(e.instance.modifiers,"hide","preventOverflow"))return e;var t=e.offsets.reference,r=M(e.instance.modifiers,function(n){return n.name==="preventOverflow"}).boundaries;if(t.bottom<r.top||t.left>r.right||t.top>r.bottom||t.right<r.left){if(e.hide===!0)return e;e.hide=!0,e.attributes["x-out-of-boundaries"]=""}else{if(e.hide===!1)return e;e.hide=!1,e.attributes["x-out-of-boundaries"]=!1}return e}function Ye(e){var t=e.placement,r=t.split("-")[0],n=e.offsets,o=n.popper,i=n.reference,f=["left","right"].indexOf(r)!==-1,s=["top","left"].indexOf(r)===-1;return o[f?"left":"top"]=i[r]-(s?o[f?"width":"height"]:0),e.placement=N(t),e.offsets.popper=y(o),e}var _e={shift:{order:100,enabled:!0,fn:ze},offset:{order:200,enabled:!0,fn:$e,offset:0},preventOverflow:{order:300,enabled:!0,fn:je,priority:["left","right","top","bottom"],padding:5,boundariesElement:"scrollParent"},keepTogether:{order:400,enabled:!0,fn:Ie},arrow:{order:500,enabled:!0,fn:Re,element:"[x-arrow]"},flip:{order:600,enabled:!0,fn:He,behavior:"flip",padding:5,boundariesElement:"viewport",flipVariations:!1,flipVariationsByContent:!1},inner:{order:700,enabled:!1,fn:Ye},hide:{order:800,enabled:!0,fn:Ue},computeStyle:{order:850,enabled:!0,fn:Ae,gpuAcceleration:!0,x:"bottom",y:"right"},applyStyle:{order:900,enabled:!0,fn:De,onLoad:Ne,gpuAcceleration:void 0}},qe={placement:"bottom",positionFixed:!1,eventsEnabled:!0,removeOnDestroy:!1,onCreate:function(){},onUpdate:function(){},modifiers:_e},B=function(){function e(t,r){var n=this,o=arguments.length>2&&arguments[2]!==void 0?arguments[2]:{};be(this,e),this.scheduleUpdate=function(){return requestAnimationFrame(n.update)},this.update=ve(this.update.bind(this)),this.options=g({},e.Defaults,o),this.state={isDestroyed:!1,isCreated:!1,scrollParents:[]},this.reference=t&&t.jquery?t[0]:t,this.popper=r&&r.jquery?r[0]:r,this.options.modifiers={},Object.keys(g({},e.Defaults.modifiers,o.modifiers)).forEach(function(f){n.options.modifiers[f]=g({},e.Defaults.modifiers[f]||{},o.modifiers?o.modifiers[f]:{})}),this.modifiers=Object.keys(this.options.modifiers).map(function(f){return g({name:f},n.options.modifiers[f])}).sort(function(f,s){return f.order-s.order}),this.modifiers.forEach(function(f){f.enabled&&K(f.onLoad)&&f.onLoad(n.reference,n.popper,n.options,f,n.state)}),this.update();var i=this.options.eventsEnabled;i&&this.enableEventListeners(),this.state.eventsEnabled=i}return we(e,[{key:"update",value:function(){return xe.call(this)}},{key:"destroy",value:function(){return Pe.call(this)}},{key:"enableEventListeners",value:function(){return Le.call(this)}},{key:"disableEventListeners",value:function(){return Ce.call(this)}}]),e}();B.Utils=(typeof window!="undefined"?window:global).PopperUtils;B.placements=ue;B.Defaults=qe;var Ge=Object.freeze(Object.defineProperty({__proto__:null,default:B},Symbol.toStringTag,{value:"Module"}));export{B as P,Ge as p};
//# sourceMappingURL=popper.e79938a8.js.map
