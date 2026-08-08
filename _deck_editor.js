const fs=require('fs');let g=fs.readFileSync('game.html','utf8'),L='\r\n';

// 1. CSS for deck editor
const css=L+'.deck-editor{width:100%;max-width:600px;max-height:70vh;overflow-y:auto}'+L+'.deck-section{margin:12px 0}'+L+'.deck-section h4{color:var(--gold);font-size:13px;letter-spacing:2px;margin-bottom:6px}'+L+'.deck-cards{display:flex;flex-wrap:wrap;gap:6px}'+L+'.deck-card{width:70px;height:95px;border:2px solid var(--border-mid);border-radius:4px;text-align:center;cursor:pointer;transition:all .2s;font-size:10px;background:var(--bg-card);color:var(--text-light);display:flex;flex-direction:column;align-items:center;justify-content:center}'+L+'.deck-card:hover{border-color:var(--gold);transform:translateY(-2px)}'+L+'.deck-card .dc-icon{font-size:22px}'+L+'.deck-card .dc-count{font-size:9px;color:var(--gold);margin-top:2px}'+L+'.deck-card .dc-btn{font-size:16px;color:var(--gold);cursor:pointer;margin-top:2px}'+L+'.deck-card.removed{opacity:.3;border-style:dashed}'+L+'.deck-summary{text-align:center;color:var(--text-dim);font-size:12px;margin:10px 0}'+L+'.deck-card.atk{border-color:#8b4a5e}'+L+'.deck-card.def{border-color:#3d7a7a}'+L+'.deck-card.skill{border-color:var(--gold)}'+L;

// 2. HTML for deck editor modal
const html=L+'<div class="modal-overlay" id="deckModal"><div class="modal deck-editor"><h3>🃏 编 辑 卡 组</h3>'+L+'<div class="deck-summary" id="deckSummary">卡组上限12张 · 攻击卡≥3 · 防御卡≥1</div>'+L+'<div class="deck-section"><h4>当前卡组 (<span id="deckCount">0</span>/12)</h4><div class="deck-cards" id="deckCurrent"></div></div>'+L+'<div class="deck-section"><h4>可选卡牌</h4><div class="deck-cards" id="deckPool"></div></div>'+L+'<div class="btn-row"><button class="btn-secondary" onclick="resetDeck()">重置默认</button><button class="btn-primary" id="confirmDeckBtn" onclick="confirmDeck()">确认卡组</button></div></div></div>'+L;

// 3. JS: Deck editor functions
const js=L+'let tempDeck={atk:5,def:3,skill:2},pendingGameStart=null;'+L+
'const DECK_POOL=['+L+
'  {id:"atk",icon:"⚔",name:"攻击",desc:"基础攻击(D20判定)",min:3,max:8},'+L+
'  {id:"def",icon:"🛡",name:"防御",desc:"减伤50%",min:1,max:5},'+L+
'  {id:"skill",icon:"🔥",name:"全力一击",desc:"高伤害(消耗纺锤)",min:0,max:4},'+L+
'];'+L+
'function showDeckEditor(){tempDeck={atk:5,def:3,skill:2};renderDeckEditor();document.getElementById("deckModal").classList.add("show")}'+L+
'function renderDeckEditor(){var t=tempDeck,total=t.atk+t.def+t.skill;document.getElementById("deckCount").textContent=total;var c=document.getElementById("deckCurrent");c.innerHTML="";DECK_POOL.forEach(function(p){if(t[p.id]>0){var d=document.createElement("div");d.className="deck-card "+p.id;d.innerHTML=\'<div class=dc-icon>\'+p.icon+\'</div><div>\'+p.name+\'</div><div class=dc-count>×\'+t[p.id]+\'</div><div class=dc-btn onclick=\"event.stopPropagation();adjustDeck(\\\'\'+p.id+\'\\\',-1)\">➖</div>\';c.appendChild(d)}});var pool=document.getElementById("deckPool");pool.innerHTML="";DECK_POOL.forEach(function(p){if(t[p.id]<p.max&&total<12){var d=document.createElement("div");d.className="deck-card";d.innerHTML=\'<div class=dc-icon>\'+p.icon+\'</div><div>\'+p.name+\'</div><div class=dc-desc style=font-size:9px>\'+p.desc+\'</div><div class=dc-btn onclick=\"event.stopPropagation();adjustDeck(\\\'\'+p.id+\'\\\',1)\">➕</div>\';pool.appendChild(d)}})'+L+
'function adjustDeck(id,d){var p=DECK_POOL.find(function(x){return x.id===id});if(!p)return;var nv=tempDeck[id]+d;if(nv<p.min||nv>p.max)return;var total=tempDeck.atk+tempDeck.def+tempDeck.skill;if(d>0&&total>=12)return;tempDeck[id]=nv;renderDeckEditor()}'+L+
'function resetDeck(){tempDeck={atk:5,def:3,skill:2};renderDeckEditor()}'+L+
'function confirmDeck(){meta.customDeck=JSON.parse(JSON.stringify(tempDeck));saveMeta();document.getElementById("deckModal").classList.remove("show");if(pendingGameStart)pendingGameStart()}'+L;

// 4. Update buildDeck to use customDeck
g=g.replace('function buildDeck(){var d=[],i;for(i=0;i<5;i++)d.push({type:"atk",icon:"⚔",label:"攻击",desc:"伤害(D20判定)"});for(i=0;i<3;i++)d.push({type:"def",icon:"🛡",label:"防御",desc:"减免50%伤害"});for(i=0;i<2;i++)d.push({type:"skill",icon:"🔥",label:"全力一击",desc:"伤害x2",cost:5});',
    'function buildDeck(){var cd=meta.customDeck||{atk:5,def:3,skill:2};var d=[],i;for(i=0;i<cd.atk;i++)d.push({type:"atk",icon:"⚔",label:"攻击",desc:"伤害(D20判定)"});for(i=0;i<cd.def;i++)d.push({type:"def",icon:"🛡",label:"防御",desc:"减免50%伤害"});for(i=0;i<cd.skill;i++)d.push({type:"skill",icon:"🔥",label:"全力一击",desc:"伤害x2",cost:5});');

// 5. Insert CSS, HTML, JS
g=g.replace('</style>',css+'</style>');
g=g.replace('<!-- ====== 商店弹窗 ====== -->',html+L+'<!-- ====== 商店弹窗 ====== -->');
g=g.replace('</script>'+L,js+'</script>'+L);

// 6. Modify game start: move logic into function, show deck editor first
const startLogic='    const genre = GENRES[Math.floor(Math.random() * GENRES.length)];'+L;
// Find the game start code and wrap it
g=g.replace(
    '    saveMeta();'+L+'    const genre = GENRES[Math.floor(Math.random() * GENRES.length)];',
    '    saveMeta();'+L+'    pendingGameStart = function(){'+L+'    const genre = GENRES[Math.floor(Math.random() * GENRES.length)];');

// Find the sendToAI line and close the function, then show deck editor
g=g.replace(
    '    sendToAI(`[题材:${genre}] ${pick} ${DEFAULT_OPENING}`, true);'+L+'});
',
    '    sendToAI(`[题材:${genre}] ${pick} ${DEFAULT_OPENING}`, true);'+L+'    };'+L+'    showDeckEditor();'+L+'});
');

// VERIFY
const si=g.indexOf('<script>')+8,ei=g.lastIndexOf('</script>'),code=g.slice(si,ei);
let o=0,c=0;for(const ch of code){if(ch==='{')o++;if(ch==='}')c++;}
try{new Function(code);console.log('JS: OK')}catch(e){console.log('JS:',e.message)}
console.log('Script:',(g.match(/<script[^>]*>/g)||[]).length,(g.match(/<\/script>/g)||[]).length);
console.log('Braces:',o,c,o===c?'OK':'ERR('+(o-c)+')');
console.log('deckEditor:',g.includes('showDeckEditor'),g.includes('customDeck'));
fs.writeFileSync('game.html',g);
console.log('DONE:',g.length);
