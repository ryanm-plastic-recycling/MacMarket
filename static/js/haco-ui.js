(function(){
  // ===== HACO big-arrow overlay helper =====
  // Usage after your series.setData(bars):
  //   HACOOverlay.attach({
  //     container: document.getElementById('haco-chart'),
  //     chart,
  //     series: priceSeries,
  //     bars
  //   });
  //
  // `bars` should be an array of { time, open, high, low, close, upw?, dnw? }
  // If you use different flags, map them before calling attach().
  const HACOOverlay = (function(){
    function ensureOverlay(container){
      let el = container.querySelector('.haco-overlay');
      if (!el) {
        el = document.createElement('div');
        el.className = 'haco-overlay';
        // Important: appendChild (do NOT assign innerHTML on container)
        container.appendChild(el);
      }
      // Enforce safety styles even if global CSS changes
      el.style.background = 'transparent';
      el.style.pointerEvents = 'none';
      return el;
    }

    function computeMarkersFromBars(bars){
      const out = [];
      for (const b of (bars || [])) {
        if (b?.upw)  out.push({ time: b.time, price: b.low  ?? b.close, dir: 'up'   });
        if (b?.dnw)  out.push({ time: b.time, price: b.high ?? b.close, dir: 'down' });
      }
      return out;
    }

    function placeArrow({chart, series, overlay, m}){
      const x = chart.timeScale().timeToCoordinate(m.time);
      const y = series.priceToCoordinate(m.price);
      if (x == null || y == null) return;
      const el = document.createElement('div');
      el.className = `haco-arrow ${m.dir}`;
      el.textContent = m.dir === 'up' ? '▲' : '▼';
      el.style.transform = `translate(${x}px, ${y}px)`;
      overlay.appendChild(el);
    }

    function attach({container, chart, series, bars, markers}){
      if (!container || !chart || !series) return;
      const overlay = ensureOverlay(container);
      let data = Array.isArray(markers) ? markers : computeMarkersFromBars(bars);
      if (!Array.isArray(data)) data = [];

      const redraw = () => {
        overlay.innerHTML = ''; // safe: overlay-only
        for (const m of data) placeArrow({chart, series, overlay, m});
      };

      // Keep aligned on pan/zoom and resize
      const ro = new ResizeObserver(() => requestAnimationFrame(redraw));
      ro.observe(container);
      chart.timeScale().subscribeVisibleTimeRangeChange(() => requestAnimationFrame(redraw));
      // Fallback: also redraw on a small delay if initial coordinates are null
      setTimeout(redraw, 0);
      setTimeout(redraw, 50);

      // expose a tiny API for external updates (optional)
      return {
        updateMarkers(next) { data = Array.isArray(next) ? next : data; redraw(); },
        redraw
      };
    }

    return { attach };
  })();

  // Make available to existing HACO code
  window.HACOOverlay = HACOOverlay;
})();

async function fetchHaco(){
    const symbol = document.getElementById('haco-symbol').value.trim();
    const timeframe = document.getElementById('haco-timeframe').value.trim();
    const lenUp = document.getElementById('haco-lenUp').value;
    const lenDown = document.getElementById('haco-lenDown').value;
    const alertLookback = document.getElementById('haco-alertLookback').value;
    const lookback = document.getElementById('haco-lookback').value;
    const url = `/api/signals/haco?symbol=${encodeURIComponent(symbol)}&timeframe=${encodeURIComponent(timeframe)}&lengthUp=${lenUp}&lengthDown=${lenDown}&alertLookback=${alertLookback}&lookback=${lookback}`;
    const res = await fetch(url);
    if(!res.ok){
        alert('No data');
        return;
    }
    const data = await res.json();
    renderChart(data.series);
    explainLast(data.last);
}

function renderChart(series){
    const chartEl = document.getElementById('haco-chart');
    chartEl.textContent = '';
    const chart = LightweightCharts.createChart(chartEl, {height:400, width: chartEl.clientWidth});

    const signalChartEl = document.getElementById('haco-signal-chart');
    if(signalChartEl){
        signalChartEl.textContent = '';
    }
    const signalChart = LightweightCharts.createChart(signalChartEl, {
        height:100,
        width: signalChartEl.clientWidth,
        timeScale:{visible:false},
        rightPriceScale:{visible:false},
        leftPriceScale:{visible:false}
    });
    const candleSeries = chart.addCandlestickSeries();
    const haToggle = document.getElementById('haco-toggleHa').checked;

    const markers = [];
    const candles = series.map(bar => {
        const res = {time: bar.time, open: bar.o, high: bar.h, low: bar.l, close: bar.c};
        const up = '#2ecc71', down = '#e74c3c';
        const col = (bar.state ? up : down);
        res.color = col;
        res.borderColor = col;
        res.wickColor = col;
        if(bar.upw) markers.push({time: bar.time, position:'belowBar', color:'green', shape:'text', text:'▲', size:2});
        if(bar.dnw) markers.push({time: bar.time, position:'aboveBar', color:'red', shape:'text', text:'▼', size:2});
        return res;
    });
    candleSeries.setData(candles);
    candleSeries.setMarkers(markers);
    HACOOverlay.attach({ container: chartEl, chart, series: candleSeries, bars: series });

    const zlHaU = chart.addLineSeries({color:'blue'});
    const zlClU = chart.addLineSeries({color:'orange'});
    const zlHaD = chart.addLineSeries({color:'purple'});
    const zlClD = chart.addLineSeries({color:'gray'});

    zlHaU.setData(series.map(b=>({time:b.time, value:b.ZlHaU}))); 
    zlClU.setData(series.map(b=>({time:b.time, value:b.ZlClU}))); 
    zlHaD.setData(series.map(b=>({time:b.time, value:b.ZlHaD}))); 
    zlClD.setData(series.map(b=>({time:b.time, value:b.ZlClD}))); 

    if(haToggle){
        const haSeries = chart.addCandlestickSeries({upColor:'#999', downColor:'#555'});
        haSeries.setData(series.map(b => ({
          time: b.time,
          open: b.haOpen,
          high: Math.max(b.h, b.haOpen, b.haC),
          low:  Math.min(b.l, b.haOpen, b.haC),
          close: b.haC
        })));
    }

    const signalSeries = signalChart.addHistogramSeries({
        priceScaleId:'',
        priceFormat:{type:'price', precision:0, minMove:1}
    });
    signalSeries.priceScale().applyOptions({scaleMargins:{top:0,bottom:0}});
    const signalData = series.map(b=>({time:b.time, value:1, color:b.state?'#2ecc71':'#e74c3c'}));
    signalSeries.setData(signalData);
    signalChart.timeScale().fitContent();
}

function explainLast(last){
    const el = document.getElementById('haco-explain');
    el.innerHTML = `<p>State: ${last.state} (${last.upw ? 'UP' : ''}${last.dnw ? 'DOWN' : ''})</p><p>${last.reasons}</p>`;
}

async function scan(direction){
    const list = document.getElementById('haco-scanList').value.split(',').map(s=>s.trim().toUpperCase()).filter(Boolean);
    const timeframe = document.getElementById('haco-timeframe').value.trim();
    const results = [];
    for(const sym of list){
        const url = `/api/signals/haco?symbol=${sym}&timeframe=${timeframe}&lookback=2`;
        try{
            const res = await fetch(url);
            if(!res.ok) continue;
            const data = await res.json();
            if(direction==='buy' && data.last.upw) results.push({sym, mark:'✅'});
            else if(direction==='sell' && data.last.dnw) results.push({sym, mark:'❌'});
            else results.push({sym, mark:data.last.state?'⤴':'⤵'});
        }catch(e){}
    }
    const out = results.map(r=>`${r.sym} ${r.mark}`).join('<br>');
    document.getElementById('haco-scanResults').innerHTML = out;
}

const runBtn = document.getElementById('haco-run');
if(runBtn) runBtn.addEventListener('click', fetchHaco);
const scanBuyBtn = document.getElementById('haco-scanBuy');
if(scanBuyBtn) scanBuyBtn.addEventListener('click', ()=>scan('buy'));
const scanSellBtn = document.getElementById('haco-scanSell');
if(scanSellBtn) scanSellBtn.addEventListener('click', ()=>scan('sell'));

fetchHaco();
