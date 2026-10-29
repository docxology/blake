"use strict";
function createCorpusSearch(data, mount = false) {
  const number = new Intl.NumberFormat("en-US");
  const defaults = {mode:"any",window_words:null,role:"primary",plane:null,work_id:null,whole_words:true,limit:100,context_chars:120};
  const cache = new Map();
  const roles = ["primary","editorial","unverified"];
  const planes = ["reading","erdman","xml"];
  const nonblank = text => Array.from(text).some(character => !data.whitespace.includes(character));
  const fold = text => Array.from(text, character => data.folding[character] || character).join("");
  const compare = (left, right) => {
    const a = Array.from(left, c => c.codePointAt(0)), b = Array.from(right, c => c.codePointAt(0));
    for (let i=0;i<Math.min(a.length,b.length);i++) if(a[i]!==b[i]) return a[i]-b[i];
    return a.length-b.length;
  };
  const word = character => {
    if (character === undefined || character === "") return false;
    const code = character.codePointAt(0), ranges = data.word_ranges;
    let lo=0, hi=ranges.length;
    while(lo<hi){const middle=(lo+hi)>>>1;if(ranges[middle][1]<code)lo=middle+1;else hi=middle;}
    return lo<ranges.length && ranges[lo][0]<=code;
  };
  const priorCharacter = (text, offset) => {
    if(offset===0)return "";
    const unit=text.charCodeAt(offset-1);
    return String.fromCodePoint(text.codePointAt(unit>=0xDC00&&unit<=0xDFFF?offset-2:offset-1));
  };
  const nextCharacter = (text, offset) => offset>=text.length?"":String.fromCodePoint(text.codePointAt(offset));
  function prepare(unit) {
    if(cache.has(unit.passage_id)) return cache.get(unit.passage_id);
    const parts=[], exceptions=[];
    let source=0, offset=0, delta=0;
    for(const character of unit.text){
      const value=data.folding[character] || character;
      parts.push(value);
      if(value.length!==1){delta+=value.length-1;exceptions.push({start:offset,end:offset+value.length,source,delta});}
      offset+=value.length;source++;
    }
    const prepared={text:parts.join(""),exceptions,tokens:unit.word_tokens};
    cache.set(unit.passage_id,prepared);
    return prepared;
  }
  function originalOffset(prepared, offset){
    const spans=prepared.exceptions;
    let lo=0,hi=spans.length;
    while(lo<hi){const middle=(lo+hi)>>>1;if(spans[middle].end<=offset)lo=middle+1;else hi=middle;}
    if(lo<spans.length&&offset>spans[lo].start)return null;
    return offset-(lo===0?0:spans[lo-1].delta);
  }
  function requestWithDefaults(input){
    if(input===null||typeof input!=="object"||Array.isArray(input))throw new Error("Supply a search request.");
    const allowed=new Set(["terms",...Object.keys(defaults)]);
    if(Object.keys(input).some(key=>!allowed.has(key)))throw new Error("Unknown search request field.");
    const request={...defaults,...input};
    if(!Array.isArray(request.terms)||request.terms.length<1||request.terms.length>8)throw new Error("Enter one to eight terms.");
    if(request.terms.some(term=>typeof term!=="string"||!nonblank(term)||Array.from(term).length>200))throw new Error("Each term must contain 1–200 characters and cannot be blank.");
    if(new Set(request.terms.map(fold)).size!==request.terms.length)throw new Error("Terms must be distinct after Unicode case folding.");
    if(!["any","all"].includes(request.mode))throw new Error("Choose ANY or ALL terms.");
    if(request.window_words!==null){
      if(!Number.isInteger(request.window_words)||request.window_words<1||request.window_words>200)throw new Error("Word window must be an integer between 1 and 200.");
      if(request.mode!=="all"||request.terms.length<2)throw new Error("Word window requires ALL mode and at least two distinct terms.");
    }
    if(request.role!==null&&!roles.includes(request.role))throw new Error("Unknown text role.");
    if(request.plane!==null&&!planes.includes(request.plane))throw new Error("Unknown source plane.");
    if(request.work_id!==null&&typeof request.work_id!=="string")throw new Error("Source family must be text or null.");
    if(typeof request.whole_words!=="boolean")throw new Error("Whole-word setting must be a boolean.");
    if(!Number.isInteger(request.limit)||request.limit<1||request.limit>1000)throw new Error("Returned-hit cap must be between 1 and 1,000.");
    if(!Number.isInteger(request.context_chars)||request.context_chars<0||request.context_chars>500)throw new Error("Context must be between 0 and 500 codepoints.");
    return request;
  }
  function matches(prepared,term,request){
    const needle=fold(term), found=[];
    let cursor=0,total=0;
    while(cursor<=prepared.text.length-needle.length){
      const start=prepared.text.indexOf(needle,cursor);
      if(start<0)break;
      const end=start+needle.length, originalStart=originalOffset(prepared,start), originalEnd=originalOffset(prepared,end);
      const aligned=originalStart!==null&&originalEnd!==null;
      const bounded=!request.whole_words||(!word(priorCharacter(prepared.text,start))&&!word(nextCharacter(prepared.text,end)));
      if(aligned&&bounded){
        total++;
        if(request.window_words!==null||found.length<request.limit)found.push({term,start:originalStart,end:originalEnd});
        cursor=end;
      }else cursor=start+1;
    }
    return {total,found};
  }
  function windowMatches(unit, groups, request){
    // Original codepoint token ranks, using the producer's Python Unicode table.
    const starts=[],ends=[];
    let offset=0,inside=false;
    for(const character of unit.text){
      const current=word(character);
      if(current&&!inside)starts.push(offset);
      if(!current&&inside)ends.push(offset);
      inside=current;offset++;
    }
    if(inside)ends.push(offset);
    const rank=(values,position,inclusive)=>{
      let lo=0,hi=values.length;
      while(lo<hi){const middle=(lo+hi)>>>1;if(values[middle]<position||(inclusive&&values[middle]===position))lo=middle+1;else hi=middle;}
      return lo;
    };
    const spans=groups.flatMap(group=>group.found),intervals=[],events=[];
    for(const span of spans){
      const lower=rank(starts,span.end,false)-request.window_words,upper=rank(ends,span.start,true);
      intervals.push([lower,upper]);
      if(lower<=upper)events.push([lower,span.term,1],[upper+1,span.term,-1]);
    }
    events.sort((a,b)=>a[0]-b[0]||compare(a[1],b[1])||a[2]-b[2]);
    const counts=new Map(request.terms.map(term=>[term,0])),complete=[];
    let active=0,previous=null;
    for(const [position,term,delta] of events){
      if(previous!==null&&previous<position&&active===counts.size)complete.push([previous,position-1]);
      const before=counts.get(term),after=before+delta;
      counts.set(term,after);active+=Number(after>0)-Number(before>0);previous=position;
    }
    const completeEnds=complete.map(interval=>interval[1]);
    const found=spans.filter((span,index)=>{
      const [lower,upper]=intervals[index],position=rank(completeEnds,lower,false);
      return lower<=upper&&position<complete.length&&complete[position][0]<=upper;
    });
    return [{total:found.length,found}];
  }
  function run(input){
    const request=requestWithDefaults(input), facets=new Map(), hits=[];
    let eligible=0,total=0,matched=0;
    for(const unit of data.units){
      if((request.role!==null&&unit.text_role!==request.role)||(request.plane!==null&&unit.source_plane!==request.plane)||(request.work_id!==null&&unit.work_id!==request.work_id))continue;
      eligible++;
      const prepared=prepare(unit), key=JSON.stringify([unit.work_id,unit.source_plane,unit.text_role]);
      if(!facets.has(key))facets.set(key,{work_id:unit.work_id,plane:unit.source_plane,role:unit.text_role,source_units:0,matched_units:0,occurrences:0,word_tokens:0,occurrences_per_10000_tokens:0});
      const facet=facets.get(key);facet.source_units++;facet.word_tokens+=prepared.tokens;
      let groups=request.terms.map(term=>matches(prepared,term,request));
      if(request.mode==="all"&&groups.some(group=>group.total===0))continue;
      if(request.window_words!==null)groups=windowMatches(unit,groups,request);
      const count=groups.reduce((sum,group)=>sum+group.total,0);
      if(count===0)continue;
      total+=count;matched++;facet.matched_units++;facet.occurrences+=count;
      if(hits.length>=request.limit)continue;
      const selected=groups.flatMap(group=>group.found).sort((a,b)=>a.start-b.start||a.end-b.end||compare(a.term,b.term));
      const characters=Array.from(unit.text);
      for(const hit of selected.slice(0,request.limit-hits.length)){
        const contextStart=Math.max(0,hit.start-request.context_chars);
        hits.push({term:hit.term,passage_id:unit.passage_id,work_id:unit.work_id,title:unit.title,edition_id:unit.edition_id,locator:unit.locator,source_url:unit.source_url,rights:unit.rights,plane:unit.source_plane,role:unit.text_role,text_sha256:unit.text_sha256,start:hit.start,end:hit.end,expression:characters.slice(hit.start,hit.end).join(""),context:characters.slice(contextStart,hit.end+request.context_chars).join(""),context_start:contextStart});
      }
    }
    const rows=Array.from(facets.values()).sort((a,b)=>compare(a.work_id,b.work_id)||compare(a.plane,b.plane)||compare(a.role,b.role));
    for(const row of rows)row.occurrences_per_10000_tokens=row.word_tokens===0?null:row.occurrences*10000/row.word_tokens;
    return {schema_version:1,request,corpus_pin:data.corpus_pin,scanned_source_units:data.units.length,eligible_source_units:eligible,total_occurrences:total,matched_source_units:matched,returned_hits:hits.length,truncated:total>hits.length,facets:rows,hits};
  }
  const api=Object.freeze({run});
  if (!mount) return api;
  window.blakeanSearch=api;
  const $=id=>document.getElementById(id);
  const text=(name,value,className)=>{const element=document.createElement(name);element.textContent=value;if(className)element.className=className;return element;};
  const safeSource=url=>{try{const parsed=new URL(url);return ["http:","https:"].includes(parsed.protocol)?parsed.href:null;}catch{return null;}};
  const families=Array.from(new Set(data.units.map(unit=>unit.work_id))).sort(compare);
  for(const family of families){const option=text("option",family);option.value=family;$("work-id").append(option);}
  $("corpus-summary").textContent=`${number.format(data.units.length)} verified source units · ${number.format(data.units.filter(unit=>unit.text_role==="primary").length)} primary · ${number.format(families.length)} source-family identifiers · fully offline`;
  $("method").textContent=data.semantics;
  $("index-hash").textContent=data.corpus_pin.index_sha256;
  $("manifest-hash").textContent=data.corpus_pin.projection_manifest_sha256;
  $("producer").textContent=`${data.producer_version} / Unicode ${data.unicode_version}`;
  let current=null,page=0;
  function renderMetrics(){
    $("metrics").replaceChildren();
    for(const [value,label] of [[current.total_occurrences,"matching occurrences"],[current.matched_source_units,"matched source units"],[current.eligible_source_units,"eligible source units"],[current.facets.filter(f=>f.matched_units>0).map(f=>f.work_id).filter((id,i,array)=>array.indexOf(id)===i).length,"matched source families"]]){
      const metric=text("div","","metric");metric.append(text("strong",number.format(value)),text("span",label));$("metrics").append(metric);
    }
    $("window-note").textContent=current.request.window_words===null?"Document-level "+current.request.mode.toUpperCase()+"; no word window.":`ALL within ${current.request.window_words} original word tokens; only participating occurrences count (phrase tokens included).`;
    $("cap-note").textContent=current.truncated?`Returning the first ${number.format(current.returned_hits)} of ${number.format(current.total_occurrences)} occurrences, ordered by source identity and original span. Distribution counts include every occurrence.`:`All ${number.format(current.total_occurrences)} occurrences are available below. Distribution counts retain stored source units, including repeated copies.`;
  }
  function renderFamilies(){
    const grouped=new Map();
    for(const facet of current.facets){
      if(!grouped.has(facet.work_id))grouped.set(facet.work_id,{id:facet.work_id,occurrences:0,matched:0,units:0,tokens:0});
      const row=grouped.get(facet.work_id);row.occurrences+=facet.occurrences;row.matched+=facet.matched_units;row.units+=facet.source_units;row.tokens+=facet.word_tokens;
    }
    const rows=Array.from(grouped.values()).filter(row=>row.occurrences>0).sort((a,b)=>b.occurrences-a.occurrences||compare(a.id,b.id));
    const chart=$("family-chart");chart.replaceChildren();
    if(rows.length===0){chart.append(text("p","No source family matched this query.","hint"));return;}
    for(const row of rows){
      const item=text("div","","family"),label=text("div","","family-label");
      label.append(text("strong",row.id),text("span",`${number.format(row.occurrences)} hits`));
      const rate=row.tokens===0?"no word tokens":`${(row.occurrences*10000/row.tokens).toFixed(2)} hits / 10k tokens`;
      const meter=document.createElement("meter");meter.min=0;meter.max=rows[0].occurrences;meter.value=row.occurrences;meter.setAttribute("aria-label",`${row.id}: ${row.occurrences} occurrences`);meter.textContent=String(row.occurrences);
      item.append(label,text("span",`${row.matched}/${row.units} source units · ${rate}`,"family-meta"),meter);chart.append(item);
    }
  }
  function renderMatrix(){
    const body=$("plane-role").querySelector("tbody");body.replaceChildren();
    for(const plane of planes){
      const row=document.createElement("tr"),heading=text("th",plane);heading.scope="row";row.append(heading);
      for(const role of roles){
        const selected=current.facets.filter(facet=>facet.plane===plane&&facet.role===role),units=selected.reduce((sum,facet)=>sum+facet.source_units,0),count=selected.reduce((sum,facet)=>sum+facet.occurrences,0),matched=selected.reduce((sum,facet)=>sum+facet.matched_units,0);
        const cell=text("td",units===0?"—":number.format(count));cell.append(text("span",units===0?"no eligible units":`${matched}/${units} units`));row.append(cell);
      }body.append(row);
    }
  }
  function renderHits(){
    const list=$("hits");list.replaceChildren();
    const first=page*20,last=Math.min(current.hits.length,first+20);
    $("page-status").textContent=current.hits.length===0?"No matching passages. Change the terms or source filters.":`Occurrences ${first+1}–${last} of ${number.format(current.returned_hits)} returned · ${number.format(current.total_occurrences)} total`;
    for(const hit of current.hits.slice(first,last)){
      const item=text("li","","hit"),heading=text("div","","hit-heading"),url=safeSource(hit.source_url);
      if(url){const link=text("a",`${hit.title} · ${hit.locator}`);link.href=url;link.target="_blank";link.rel="noopener noreferrer";heading.append(link);}else heading.append(text("strong",`${hit.title} · ${hit.locator}`));
      heading.append(text("span",`term: ${hit.term}`));
      const paragraph=text("p","","excerpt"),characters=Array.from(hit.context),start=hit.start-hit.context_start,end=hit.end-hit.context_start;
      paragraph.append(document.createTextNode(characters.slice(0,start).join("")),text("mark",characters.slice(start,end).join("")),document.createTextNode(characters.slice(end).join("")));
      const details=document.createElement("details");details.append(text("summary","Source identity, rights and exact span"),text("p",`${hit.passage_id} · edition ${hit.edition_id}`),text("p",`Original Unicode codepoints [${hit.start}, ${hit.end}) · SHA-256 ${hit.text_sha256}`),text("p",hit.rights));
      item.append(heading,text("p",`${hit.work_id} · ${hit.plane} / ${hit.role}`,"hit-meta"),paragraph,details);list.append(item);
    }
    $("previous-page").disabled=page===0;$("next-page").disabled=last>=current.hits.length;
  }
  function render(){renderMetrics();renderFamilies();renderMatrix();renderHits();$("results-section").hidden=false;$("download-results").disabled=false;}
  $("search-form").addEventListener("submit",event=>{
    event.preventDefault();$("search-error").hidden=true;
    const request={terms:$("terms").value.split(/\r?\n/).filter(nonblank),mode:$("mode").value,window_words:$("window-words").value.trim()===""?null:Number($("window-words").value),role:$("role").value||null,plane:$("plane").value||null,work_id:$("work-id").value||null,whole_words:$("whole-words").checked,limit:Number($("limit").value),context_chars:120};
    $("search-status").textContent="Searching local source texts…";$("submit-search").disabled=true;
    // Paint the busy state before the bounded, synchronous local search.
    setTimeout(()=>{try{const begin=performance.now();current=run(request);page=0;render();$("search-status").textContent=`${number.format(current.total_occurrences)} occurrences in ${number.format(current.matched_source_units)} of ${number.format(current.eligible_source_units)} eligible source units · ${request.window_words===null?"document "+request.mode.toUpperCase():"ALL within "+request.window_words+" original word tokens"} · ${(performance.now()-begin).toFixed(0)} ms`;}catch(error){current=null;$("results-section").hidden=true;$("download-results").disabled=true;$("search-status").textContent="Search was not run.";$("search-error").textContent=error.message;$("search-error").hidden=false;}finally{$("submit-search").disabled=false;}},0);
  });
  $("clear-search").addEventListener("click",()=>{current=null;page=0;$("search-form").reset();$("results-section").hidden=true;$("search-error").hidden=true;$("download-results").disabled=true;$("search-status").textContent="Enter a term to search. No query has run.";$("terms").focus();});
  $("previous-page").addEventListener("click",()=>{page--;renderHits();$("page-status").scrollIntoView({block:"nearest"});});
  $("next-page").addEventListener("click",()=>{page++;renderHits();$("page-status").scrollIntoView({block:"nearest"});});
  $("download-results").addEventListener("click",()=>{if(current===null)return;const blob=new Blob([JSON.stringify(current,null,2)+"\n"],{type:"application/json"}),url=URL.createObjectURL(blob),link=document.createElement("a");link.href=url;link.download="corpus-search.json";document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),0);});
  return api;
}
if(typeof module!=="undefined" && module.exports) module.exports={createCorpusSearch};
if(typeof document!=="undefined") createCorpusSearch(JSON.parse(document.getElementById("search-data").textContent),true);
