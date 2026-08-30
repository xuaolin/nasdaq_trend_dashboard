let priceChart;

function fmt(v, d=2){
  return (v === null || v === undefined || Number.isNaN(Number(v))) ? "--" : Number(v).toFixed(d);
}
function pct(v){
  if(v === null || v === undefined) return "--";
  const n = Number(v);
  return `${n >= 0 ? "+" : ""}${n.toFixed(2)}%`;
}
function colorClass(v){
  const n = Number(v);
  return n > 0 ? "positive" : n < 0 ? "negative" : "neutral";
}
function scoreColor(score){
  if(score >= 70) return "#42d392";
  if(score >= 45) return "#e6c45c";
  if(score >= 30) return "#f59e42";
  return "#ef6461";
}
function setText(id, text){ document.getElementById(id).textContent = text; }

function renderChecklist(items){
  const el = document.getElementById("checklist");
  el.innerHTML = "";
  (items || []).forEach(x => {
    const row = document.createElement("div");
    row.className = "check";
    row.innerHTML = `<span class="dot ${x.status}"></span>
      <div><b>${x.title}</b><small>${x.detail}</small></div>`;
    el.appendChild(row);
  });
}
function renderChart(rows){
  const ctx = document.getElementById("priceChart");
  if(priceChart) priceChart.destroy();

  priceChart = new Chart(ctx, {
    type: "line",
    data: {
      labels: rows.map(x => x.date),
      datasets: [
        {label:"QQQ", data:rows.map(x=>x.close), borderWidth:2.2, pointRadius:0, tension:.05},
        {label:"MA20", data:rows.map(x=>x.ma20), borderWidth:1.1, pointRadius:0},
        {label:"MA60", data:rows.map(x=>x.ma60), borderWidth:1.1, pointRadius:0},
        {label:"MA120", data:rows.map(x=>x.ma120), borderWidth:1.1, pointRadius:0},
        {label:"MA200", data:rows.map(x=>x.ma200), borderWidth:1.3, pointRadius:0}
      ]
    },
    options: {
      maintainAspectRatio:false,
      interaction:{mode:"index",intersect:false},
      plugins:{
        legend:{display:false},
        tooltip:{backgroundColor:"#07131c",borderColor:"#25465a",borderWidth:1}
      },
      scales:{
        x:{grid:{display:false},ticks:{color:"#6f8797",maxTicksLimit:8}},
        y:{grid:{color:"rgba(54,83,101,.22)"},ticks:{color:"#6f8797"}}
      }
    }
  });
}

async function boot(){
  try{
    const r = await fetch(`data/technical.json?ts=${Date.now()}`);
    if(!r.ok) throw new Error("technical.json unavailable");
    const d = await r.json();

    setText("updatedAt", d.meta.updated_at || "--");
    setText("score", Math.round(d.score.total));
    setText("state", d.score.state);
    setText("scoreTrend", d.score.trend);
    setText("action", d.signal.action);
    setText("regime", d.signal.regime);
    setText("signalLine", d.signal.message);

    const ring = document.getElementById("scoreRing");
    const c = scoreColor(d.score.total);
    ring.style.background = `conic-gradient(${c} ${d.score.total*3.6}deg,#173042 0deg)`;
    document.getElementById("state").style.color = c;

    setText("price", `$${fmt(d.market.close)}`);
    setText("dailyChange", pct(d.market.daily_change_pct));
    document.getElementById("dailyChange").className = colorClass(d.market.daily_change_pct);
    setText("vix", fmt(d.market.vix));

    ["20","60","120","200"].forEach(n => {
      setText(`ma${n}`, `$${fmt(d.market[`ma${n}`])}`);
      setText(`d${n}`, pct(d.market[`d${n}`]));
      document.getElementById(`d${n}`).className = colorClass(d.market[`d${n}`]);
    });

    setText("trendScore", fmt(d.score.components.trend,0));
    setText("momentumScore", fmt(d.score.components.momentum,0));
    setText("deviationScore", fmt(d.score.components.deviation,0));
    setText("volatilityScore", fmt(d.score.components.volatility,0));
    setText("breadthScore", fmt(d.score.components.breadth,0));
    setText("rsi", fmt(d.market.rsi14,1));
    setText("rsiState", d.market.rsi_state || "");

    setText("breadth50", d.breadth.ma50_pct == null ? "--" : `${fmt(d.breadth.ma50_pct,1)}%`);
    setText("breadth200", d.breadth.ma200_pct == null ? "--" : `${fmt(d.breadth.ma200_pct,1)}%`);
    setText("breadthNote", d.breadth.note || "");

    renderChecklist(d.checklist);
    renderChart(d.chart || []);
  }catch(err){
    console.error(err);
    setText("state","DATA ERROR");
    setText("signalLine","请先运行 GitHub Actions 的 Update Nasdaq Technical Data workflow。");
  }
}
boot();
