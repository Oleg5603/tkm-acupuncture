const state={all:[],filtered:[],shown:9,selected:new Set(),query:''};
const $=s=>document.querySelector(s);
const escapeHtml=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const normalize=s=>String(s??'').toLocaleLowerCase('ru-RU').replace(/ё/g,'е').replace(/[-–—.]/g,' ');
const clean=s=>String(s??'').replace(/www\.eledia\.ru/gi,'').replace(/^\s*\d+\s*/,'').replace(/\s+/g,' ').trim();

function friendlyTitle(item){
  const raw=clean(item.title);
  if(raw.length>8&&!/^\d+[.)]?$/.test(raw)) return raw.slice(0,100);
  const lines=String(item.description||'').split('\n').map(clean).filter(x=>x.length>4&&!/^\d+$/.test(x));
  return (lines.find(x=>/[А-ЯA-Z]\d+|бол|точк|синдром|наруш|сустав/i.test(x))||lines[0]||`Материал со страницы ${item.page}`).slice(0,100);
}
function excerpt(item){
  const text=clean(item.description).replace(/^\d+\s*/, '');
  return text.length>230?`${text.slice(0,227).trim()}…`:text;
}
function applySearch(query){
  state.query=query.trim();
  const words=normalize(state.query).split(/\s+/).filter(Boolean);
  state.filtered=state.all.filter(item=>words.every(word=>normalize(`${item.title} ${item.description}`).includes(word)));
  state.shown=9;
  document.querySelectorAll('[data-query]').forEach(b=>b.classList.toggle('active',normalize(b.dataset.query)===normalize(state.query)));
  render();
}
function render(){
  const items=state.filtered.slice(0,state.shown);
  $('#resultLabel').textContent=state.query?`Результаты по запросу «${state.query}»`:'Материалы атласа';
  $('#resultCount').textContent=state.query?`Найдено: ${state.filtered.length}`:`Доступно ${state.filtered.length} материалов`;
  $('#atlasGrid').innerHTML=items.map(item=>`<article class="atlas-card">
    <button class="atlas-image" type="button" data-detail="${item.id}" aria-label="Открыть материал"><img src="${escapeHtml(item.image)}" alt="Схема расположения точек, страница ${item.page}" loading="lazy"></button>
    <div class="card-content"><div class="card-meta"><span>Атлас Леднёва · стр. ${item.page}</span><label class="pick-check"><input type="checkbox" data-id="${item.id}" ${state.selected.has(item.id)?'checked':''}> В памятку</label></div>
    <h3>${escapeHtml(friendlyTitle(item))}</h3><p>${escapeHtml(excerpt(item))}</p><button type="button" data-detail="${item.id}">Посмотреть расположение →</button></div>
  </article>`).join('')||`<div class="empty"><b>Точных совпадений не найдено</b><p>Попробуйте более короткую формулировку, название точки или область тела.</p></div>`;
  $('#loadMore').hidden=state.shown>=state.filtered.length;
  updateSelected();
}
function updateSelected(){
  $('#selectedCount').textContent=state.selected.size;
  $('#selectedTools').hidden=!state.selected.size;
}
function showDetail(id){
  const item=state.all.find(x=>x.id===id);if(!item)return;
  $('#dialogContent').innerHTML=`<p class="eyebrow dark">Атлас Леднёва · страница ${item.page}</p><h2>${escapeHtml(friendlyTitle(item))}</h2><img class="detail-image" src="${escapeHtml(item.image)}" alt="Локализация точек, страница ${item.page}"><h3>Описание из атласа</h3><p class="detail-text">${escapeHtml(clean(item.description))}</p>`;
  $('#detailDialog').showModal();
}
function selectedItems(){return state.all.filter(item=>state.selected.has(item.id));}
function exportText(items){return items.map(x=>`${friendlyTitle(x)}\nИсточник: Атлас Леднёва, страница ${x.page}\n\n${clean(x.description)}`).join('\n\n---\n\n');}
function download(name,type,content){const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([content],{type}));a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000)}
function exportItems(kind){
  const items=selectedItems();if(!items.length)return;
  const text=exportText(items);
  if(kind==='txt')download('pamyatka-tkm.txt','text/plain;charset=utf-8',text);
  if(kind==='word'){const body=items.map(x=>`<h1>${escapeHtml(friendlyTitle(x))}</h1><p><b>Источник:</b> Атлас Леднёва, страница ${x.page}</p><img src="${new URL(x.image,location.href).href}" style="max-width:650px"><p>${escapeHtml(clean(x.description)).replace(/\n/g,'<br>')}</p>`).join('<hr>');download('pamyatka-tkm.doc','application/msword;charset=utf-8',`<!doctype html><meta charset="utf-8"><body>${body}</body>`)}
  if(kind==='pdf'){const w=open('','_blank');w.document.write(`<!doctype html><meta charset="utf-8"><title>Памятка ТКМ</title><style>body{font-family:Arial;max-width:800px;margin:auto}img{max-width:100%;page-break-inside:avoid}article{page-break-after:always;white-space:pre-wrap}</style>${items.map(x=>`<article><h1>${escapeHtml(friendlyTitle(x))}</h1><p>Атлас Леднёва, стр. ${x.page}</p><img src="${new URL(x.image,location.href).href}"><p>${escapeHtml(clean(x.description))}</p></article>`).join('')}`);w.document.close();setTimeout(()=>w.print(),700)}
  $('#exportDialog').close();
}

$('#searchForm').addEventListener('submit',e=>{e.preventDefault();applySearch($('#search').value)});
$('#search').addEventListener('search',()=>applySearch($('#search').value));
$('#clearFilters').addEventListener('click',()=>{$('#search').value='';applySearch('')});
$('#loadMore').addEventListener('click',()=>{state.shown+=9;render()});
document.addEventListener('change',e=>{if(e.target.matches('[data-id]')){const id=Number(e.target.dataset.id);e.target.checked?state.selected.add(id):state.selected.delete(id);updateSelected()}});
document.addEventListener('click',e=>{
  const quick=e.target.closest('[data-query]');if(quick){$('#search').value=quick.dataset.query;applySearch(quick.dataset.query);$('#resultCount').scrollIntoView({behavior:'smooth',block:'center'})}
  const detail=e.target.closest('[data-detail]');if(detail)showDetail(Number(detail.dataset.detail));
  if(e.target.closest('[data-open-export]'))$('#exportDialog').showModal();
  if(e.target.closest('[data-close-dialog]'))e.target.closest('dialog').close();
  const exp=e.target.closest('[data-export]');if(exp)exportItems(exp.dataset.export);
});
document.querySelectorAll('dialog').forEach(d=>d.addEventListener('click',e=>{if(e.target===d)d.close()}));

const metricKey='tkm_lednev_visits';const visits=Number(localStorage.getItem(metricKey)||0)+1;localStorage.setItem(metricKey,String(visits));$('#localVisits').textContent=visits;
const started=Date.now();setInterval(()=>{const seconds=Math.floor((Date.now()-started)/1000);$('#sessionTime').textContent=`${String(Math.floor(seconds/60)).padStart(2,'0')}:${String(seconds%60).padStart(2,'0')}`},1000);

fetch('assets/atlas-data.json').then(r=>{if(!r.ok)throw new Error(`HTTP ${r.status}`);return r.json()}).then(data=>{state.all=data.items||[];state.filtered=state.all;render()}).catch(()=>{$('#resultCount').textContent='Не удалось загрузить атлас';$('#atlasGrid').innerHTML='<div class="empty">Обновите страницу или попробуйте позднее.</div>'});
