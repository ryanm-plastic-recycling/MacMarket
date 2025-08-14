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
    chartEl.innerHTML = '';
    const chart = LightweightCharts.createChart(chartEl, {height:400, width: chartEl.clientWidth});

    const signalChartEl = document.getElementById('haco-signal-chart');
    if(signalChartEl){
        signalChartEl.innerHTML = '';
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
