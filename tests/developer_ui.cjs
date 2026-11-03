// Exercise the standalone developer page's search and anchor reset without a browser.
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const html = fs.readFileSync(process.argv[2] || 'output/semantic/developer.html', 'utf8');
const cards = [...html.matchAll(/<article class="axis"[^>]*>(.*?)<\/article>/gs)].map(m=>({textContent:m[1].replace(/<[^>]*>/g,''),hidden:false}));
let inputHandler, hashHandler;
const search={value:'',addEventListener:(name,fn)=>{assert.equal(name,'input');inputHandler=fn;}};
const counter={textContent:''};
const location={hash:''};
const document={getElementById:id=>id==='axis-search'?search:counter,querySelectorAll:()=>cards};
vm.runInNewContext(html.match(/<script>(.*?)<\/script>/s)[1],{document,location,addEventListener:(name,fn)=>{assert.equal(name,'hashchange');hashHandler=fn;}});
assert.equal(cards.length,38);
search.value='verification';inputHandler();assert.equal(cards.filter(c=>!c.hidden).length,1);
search.value='存在しない観点の名前';inputHandler();assert.equal(cards.filter(c=>!c.hidden).length,0);assert.equal(counter.textContent,'0 / 38 観点');
location.hash='#axis-ownership';hashHandler();assert.equal(cards.filter(c=>!c.hidden).length,38);assert.equal(search.value,'');
console.log('Developer page behavior passed: 38 axes, search, empty state, and anchor reset.');
