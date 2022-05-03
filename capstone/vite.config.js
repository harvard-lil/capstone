import { defineConfig } from 'vite'
import { createVuePlugin } from 'vite-plugin-vue2'
import { readdirSync, lstatSync } from "fs"
import { resolve } from "path"
import { visualizer } from "rollup-plugin-visualizer"


// import { createSvgPlugin } from "vite-plugin-vue2-svg";
// custom svg plugin, pending either migration to Vue 3, or fix for
// https://github.com/pakholeung37/vite-plugin-vue2-svg/issues/3
// otherwise could be createSvgPlugin({svgoConfig:{plugins: [{cleanupIDs: false}]}})
import { compileTemplate, parse } from "@vue/component-compiler-utils"
import { readFileSync } from "fs"
import { basename } from "path"
import * as compiler from "vue-template-compiler"
const svgPlugin = {
  name: "custom-svg",
  async transform(_source, id) {
    const svgPath = id.split('?', 1)[0];
    if (!svgPath.endsWith('.svg'))
      return null;
    let svg = readFileSync(svgPath, { encoding: "utf-8" });
    svg = svg.replace('<svg', '<svg v-on="$listeners"');
    const filename = `${basename(id)}.vue`;
    const template = parse({source: `<template>${svg}</template>`, compiler, filename}).template;
    if (!template)
      return "";
    const result = compileTemplate({source: template.content, compiler, filename});
    return `${result.code}\nexport default {render: render}`;
  },
};


// we only want to watch the files in watchFiles.
// pending https://github.com/vitejs/vite/issues/7850 ,
// the workaround is to ignore everything in the current dir EXCEPT those files ...
const watchFiles = ['static', 'vite.config.js'];
const ignoreFiles = readdirSync('.').filter(file => !watchFiles.includes(file)).map(file => {
  if (lstatSync(file).isDirectory()) file += '/**';
  return resolve(file);
});


// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    createVuePlugin(),
    svgPlugin,
    // to write bundle sizes to stats.html:
    // visualizer({gzipSize: true}),
  ],
  base: '/static/',  // same as settings.STATIC_URL
  server: {
    host: '0.0.0.0',
    port: 8080,
    watch: {
      ignored: ignoreFiles,
      usePolling: true,
    },
    hmr: false,  // disable hot module replacement
  },
  // for Tone.js, shim "global" to undefined
  // define: {
  //   "global": undefined,
  // },
  // https://github.com/underfin/vite-plugin-vue2/issues/111
  resolve: {
    alias: {
      'vue': require.resolve('vue/dist/vue.js'),
    },
  },
  build: {
    manifest: true,
    outDir: 'static/dist',  // same as settings.DJANGO_VITE_ASSETS_PATH
    sourcemap: true,
    devSourcemap: true,
    rollupOptions: {
      input: {
        base: 'static/js/base.js',
        map: 'static/js/homepage-map/main.js',
        limericks: 'static/js/generate_limericks.js',
        witchcraft: 'static/js/witchcraft/main.js',
        search: 'static/js/search/main.js',
        trends: 'static/js/trends/main.js',
        case: 'static/js/case/main.js',
        'cite-grid': 'static/js/cite-grid/main.js',
        'case-editor': 'static/js/case-editor/main.js',
        'labs-chronolawgic': 'static/js/labs/chronolawgic/main.js',
      }
    }
  }
})
