(function(){
const $=s=>document.querySelector(s);
const msgs=$("#chatMessages"),input=$("#chatInput"),form=$("#chatForm");
if(!msgs)return;
// 1) quick-question chips
const chips=document.createElement("div");chips.className="sg-chips";
["📅 Exam date sheet","💰 Fee structure","📚 Show all courses","📖 Library timings","🏠 Hostel info","🎓 Scholarships"].forEach((t,i)=>{
  const b=document.createElement("button");b.type="button";b.className="sg-chip";b.style.animationDelay=i*70+"ms";b.textContent=t;
  b.onclick=()=>{input.value=t.replace(/^\S+\s/,"");form.requestSubmit()};chips.appendChild(b)});
msgs.parentNode.insertBefore(chips,msgs.nextSibling);
// 2) typing dots while waiting for /api/chat
const _f=window.fetch;
window.fetch=function(u,o){
  if(String(u).includes("/api/chat")){
    const t=document.createElement("div");t.className="message assistant-message";
    t.innerHTML='<div class="message-avatar">S</div><div class="message-content"><span class="sg-typing"><i></i><i></i><i></i></span></div>';
    msgs.appendChild(t);msgs.scrollTop=msgs.scrollHeight;
    return _f.apply(this,arguments).finally(()=>t.remove());
  }
  return _f.apply(this,arguments);
};
// 3a) render markdown pipe-tables (timetables) as real HTML tables
function esc(t){return t.replace(/[&<>]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;"}[c]))}
function renderTables(m){
  const b=m.querySelector(".message-bubble");
  if(!b||b.dataset.tbl||!/^\|.*\|\s*$/m.test(b.textContent))return;
  b.dataset.tbl=1;const out=[];let rows=[];
  const flush=()=>{if(!rows.length)return;
    const cells=r=>r.trim().replace(/^\||\|$/g,"").split("|").map(x=>x.trim());
    const body=rows.filter(r=>!/^\|\s*:?-{2,}/.test(r)).map(cells);
    out.push('<div class="sg-table-wrap"><table class="sg-table"><thead><tr>'+body[0].map(c=>"<th>"+esc(c)+"</th>").join("")+"</tr></thead><tbody>"+
      body.slice(1).map(r=>"<tr>"+r.map(c=>'<td'+(c?"":' class="sg-empty"')+">"+esc(c)+"</td>").join("")+"</tr>").join("")+"</tbody></table></div>");rows=[]};
  b.textContent.split("\n").forEach(l=>{if(/^\|.*\|\s*$/.test(l))rows.push(l);else{flush();if(l.trim())out.push("<div>"+esc(l)+"</div>")}});flush();
  b.innerHTML=out.join("");b.style.whiteSpace="normal";
}
// 3) copy + read-aloud buttons on every assistant reply
function addTools(m){
  if(m.dataset.tools||!m.classList.contains("assistant-message"))return;
  const c=m.querySelector(".message-content");if(!c||c.querySelector(".sg-typing"))return;
  renderTables(m);m.dataset.tools=1;const w=document.createElement("div");w.className="sg-tools";
  const cp=document.createElement("button");cp.className="sg-tool";cp.textContent="📋 Copy";
  cp.onclick=()=>{navigator.clipboard.writeText(c.innerText);toast("Copied!")};
  const sp=document.createElement("button");sp.className="sg-tool";sp.textContent="🔊 Listen";
  sp.onclick=()=>{
    if(speechSynthesis.speaking||speechSynthesis.pending){speechSynthesis.cancel();document.querySelectorAll(".sg-tool.sg-speaking").forEach(b=>{b.textContent="🔊 Listen";b.classList.remove("sg-speaking")});return}
    const t=c.cloneNode(true);t.querySelectorAll(".sg-tools").forEach(x=>x.remove());
    const u=new SpeechSynthesisUtterance(t.innerText.replace(/[|\t]+/g,", ").replace(/-{3,}/g," "));
    u.onend=u.onerror=()=>{sp.textContent="🔊 Listen";sp.classList.remove("sg-speaking")};
    sp.textContent="⏹ Stop";sp.classList.add("sg-speaking");speechSynthesis.speak(u)};
  w.append(cp,sp);c.appendChild(w);
}
new MutationObserver(l=>l.forEach(r=>r.addedNodes.forEach(n=>n.nodeType===1&&addTools(n)))).observe(msgs,{childList:true});
// 4) voice input (Chrome/Edge)
const SR=window.SpeechRecognition||window.webkitSpeechRecognition;
if(SR){const mic=document.createElement("button");mic.type="button";mic.className="sg-mic";mic.textContent="🎤";mic.title="Speak your question";
  const rec=new SR();rec.lang="en-IN";rec.onresult=e=>{input.value=e.results[0][0].transcript;form.requestSubmit()};
  rec.onend=()=>mic.classList.remove("on");mic.onclick=()=>{mic.classList.add("on");rec.start()};
  $("#sendButton").before(mic);}
// 5) dark/light toggle (remembered)
const tb=document.createElement("button");tb.className="sg-theme";document.body.appendChild(tb);
const setT=l=>{document.body.classList.toggle("sg-light",l);tb.textContent=l?"🌙 Dark":"☀️ Light";try{localStorage.setItem("sgTheme",l?"l":"d")}catch(e){}};
let saved=null;try{saved=localStorage.getItem("sgTheme")}catch(e){}setT(saved==="l");tb.onclick=()=>setT(!document.body.classList.contains("sg-light"));

// 6) global stop-voice button + stop speech when a new question is sent / page closes
const sb=document.createElement("button");sb.className="sg-theme sg-stopvoice";sb.textContent="⏹ Stop voice";sb.style.display="none";
sb.onclick=()=>speechSynthesis.cancel();document.body.appendChild(sb);
setInterval(()=>{sb.style.display=(speechSynthesis.speaking||speechSynthesis.pending)?"block":"none"},300);
form.addEventListener("submit",()=>speechSynthesis.cancel());
window.addEventListener("beforeunload",()=>speechSynthesis.cancel());
// 7) multi-select chips for the admin upload (several branches / semesters at once)
function multiChips(id,allLabel){
  const sel=document.getElementById(id);if(!sel)return;
  const vals=[...sel.options].map(o=>o.value).filter(v=>v!=="ALL");
  const box=document.createElement("div");box.className="sg-chips";const on=new Set();
  const apply=()=>{const v=on.size?[...on].join(","):"ALL";
    sel.innerHTML="";const o=document.createElement("option");o.value=v;o.textContent=v==="ALL"?allLabel:v;o.selected=true;sel.appendChild(o);
    box.querySelectorAll(".sg-chip").forEach(b=>b.classList.toggle("sg-on",b.dataset.v==="ALL"?!on.size:on.has(b.dataset.v)))};
  [["ALL",allLabel],...vals.map(v=>[v,v==="AI_DS"?"AI & DS":v])].forEach(([v,l])=>{
    const b=document.createElement("button");b.type="button";b.className="sg-chip";b.dataset.v=v;b.textContent=(/^\d$/.test(v)?"Sem ":"")+l;
    b.onclick=()=>{if(v==="ALL")on.clear();else on.has(v)?on.delete(v):on.add(v);apply()};box.appendChild(b)});
  sel.style.display="none";sel.parentNode.appendChild(box);apply();
}
multiChips("uploadBranch","All Branches");multiChips("uploadSemester","All Semesters");
function toast(t){const d=document.createElement("div");d.className="sg-toast";d.textContent=t;document.body.appendChild(d);setTimeout(()=>d.remove(),1500)}
})();
